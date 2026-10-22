#!/usr/bin/env python3
"""Install/check the explicit BakaSU legacy-init bridge for current SUSFS.

Usage: bakasu_susfs_compat.py <KernelSU/kernel> <kernel common> [--check]

Only the versioned downstream BakaSU profile is accepted. This does NOT add
KernelSU's preinit runner: it preserves BakaSU's existing init.rc/ksud path.
The same header is inspected by susfs_ksu_check.py and by BakaSU's Kbuild.
"""
import argparse
import re
from pathlib import Path

HEADER = "bakasu_susfs_compat.h"
PREINIT_SYMBOLS = ("ksu_setup_preinit_file", "ksu_preinit_handle_post_execveat")
INCLUDE = f"#include <linux/{HEADER}>"
BRIDGE = ("/* BakaSU: retain the existing init.rc/ksud boot path; no preinit runner. */\n"
          + INCLUDE + "\n")


class CompatError(ValueError):
    pass


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def load_profile(ksu: Path) -> str:
    """Return the header verbatim; fail rather than assuming any BakaSU is fixed."""
    path = ksu / "include" / HEADER
    if not path.is_file():
        raise CompatError(f"{path}: missing versioned downstream BakaSU profile")
    header = path.read_text()
    clean = strip_comments(header)
    versions = re.findall(r"^\s*#\s*define\s+BAKASU_SUSFS_COMPAT_VERSION\s+(\d+)\s*$", clean, re.M)
    if versions != ["1"]:
        raise CompatError("unsupported or ambiguous BAKASU_SUSFS_COMPAT_VERSION (expected 1)")
    expected = (r"#\s*ifdef\s+CONFIG_KSU_SUSFS\s*\n"
                r"\s*#\s*define\s+KSU_NO_PREINIT\s+1\s*\n"
                r"\s*#\s*endif\b")
    if (not re.search(expected, clean)
            or len(re.findall(r"#\s*define\s+KSU_NO_PREINIT\b", clean)) != 1
            or re.search(r"#\s*undef\s+KSU_NO_PREINIT\b", clean)):
        raise CompatError("profile must explicitly define KSU_NO_PREINIT=1 under CONFIG_KSU_SUSFS")
    # Version 1 is deliberately a small, exact preprocessor contract. Do not
    # accept a matching #define hidden inside #if 0 or an unexpected #else.
    directives = [re.sub(r"\s+", " ", re.sub(r"^\s*#\s*", "#", line)).strip()
                  for line in clean.splitlines() if line.strip()]
    expected_directives = [
        "#ifndef __BAKASU_SUSFS_COMPAT_H", "#define __BAKASU_SUSFS_COMPAT_H",
        "#define BAKASU_SUSFS_COMPAT_VERSION 1", "#ifdef CONFIG_KSU_SUSFS",
        "#define KSU_NO_PREINIT 1", "#endif", "#endif",
    ]
    if directives != expected_directives:
        raise CompatError("profile v1 preprocessor contract has changed; review the integration")
    return header


def _known_condition(directive: str, expression: str):
    """Only evaluate the selected preinit macro; all CONFIG conditions are unknown.

    Unknown branches are BOTH retained. This is intentionally conservative,
    not a substitute for a C preprocessor, type checking or an actual build.
    """
    expression = expression.strip()
    if directive in ("ifdef", "ifndef"):
        if expression != "KSU_NO_PREINIT":
            return None
        return directive == "ifdef"
    expression = re.sub(r"\s+", "", expression)
    if expression in ("defined(KSU_NO_PREINIT)", "definedKSU_NO_PREINIT", "KSU_NO_PREINIT", "1"):
        return True
    if expression in ("!defined(KSU_NO_PREINIT)", "!definedKSU_NO_PREINIT", "!KSU_NO_PREINIT", "0"):
        return False
    return None


def without_preinit_blocks(lines: list) -> list:
    """Remove only provably inactive branches with KSU_NO_PREINIT=1.

    Patch fragments can contain unmatched CONFIG #endif context. Unknown
    conditions remain conservative; complete files are checked again after
    patching. No preinit symbol is ever unconditionally allowlisted.
    """
    out, stack = [], []
    active = True
    for line in lines:
        match = re.match(r"\s*#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)", line)
        if match:
            directive, expression = match.groups()
            if directive in ("if", "ifdef", "ifndef"):
                value = _known_condition(directive, expression)
                stack.append({"parent": active, "taken": value is True})
                active = active and value is not False
            elif directive in ("elif", "else") and stack:
                frame = stack[-1]
                value = True if directive == "else" else _known_condition("if", expression)
                active = frame["parent"] and not frame["taken"] and value is not False
                frame["taken"] = frame["taken"] or value is True
            elif directive == "endif":
                active = stack.pop()["parent"] if stack else True
            continue
        if active:
            out.append(line)
    return out


def guarded_preinit_lines(lines: list) -> list:
    """Ensure ALL preinit references are guarded before omitting declarations."""
    clean = strip_comments("\n".join(lines)).splitlines()
    filtered = without_preinit_blocks(clean)
    remaining = "\n".join(filtered)
    for symbol in PREINIT_SYMBOLS:
        if re.search(r"\b" + symbol + r"\b", remaining):
            raise CompatError(f"{symbol}: reference is not protected by KSU_NO_PREINIT")
    return filtered


def install(ksu: Path, common: Path, check_only: bool = False) -> bool:
    header = load_profile(ksu)
    makefile = common / "Makefile"
    if not makefile.is_file():
        raise CompatError(f"{makefile}: not a kernel source tree")
    release = makefile.read_text()
    if (not re.search(r"^VERSION\s*=\s*5\s*$", release, re.M)
            or not re.search(r"^PATCHLEVEL\s*=\s*10\s*$", release, re.M)):
        raise CompatError("this BakaSU bridge only supports Linux 5.10")

    exec_path = common / "fs/exec.c"
    if not exec_path.is_file():
        raise CompatError(f"{exec_path}: missing")
    source = exec_path.read_text()
    clean = strip_comments(source)
    for symbol in PREINIT_SYMBOLS:
        if not re.search(r"\b" + symbol + r"\b", clean):
            raise CompatError(f"{exec_path}: current SUSFS hook {symbol} is missing")
    guarded_preinit_lines(source.splitlines())
    if re.search(r"#\s*(?:define|undef)\s+KSU_NO_PREINIT\b", clean):
        raise CompatError("fs/exec.c has an unmanaged KSU_NO_PREINIT definition")

    anchor = "#include <linux/susfs_def.h>\n"
    if source.count(anchor) != 1:
        raise CompatError("fs/exec.c: expected exactly one SUSFS header include")
    if source.count(INCLUDE) > 1:
        raise CompatError("fs/exec.c: duplicate BakaSU compatibility header")
    first_hook = min(source.index(sym) for sym in PREINIT_SYMBOLS)
    if source.index(anchor) > first_hook:
        raise CompatError("fs/exec.c: SUSFS header must precede the preinit hooks")
    if INCLUDE in source and source.index(INCLUDE) > first_hook:
        raise CompatError("fs/exec.c: BakaSU header must precede the preinit hooks")

    for rel, symbols in (
        ("security/selinux/hooks.c", ("ksu_selinux_hide_running", "my_setprocattr")),
        ("security/selinux/selinuxfs.c", ("my_write_context", "my_write_access")),
    ):
        path = common / rel
        if not path.is_file():
            raise CompatError(f"{path}: missing current SUSFS SELinux integration")
        text = strip_comments(path.read_text())
        if any(not re.search(r"\b" + sym + r"\b", text) for sym in symbols):
            raise CompatError(f"{path}: missing current SUSFS SELinux integration")

    runtime = ksu / "runtime/ksud_integration.c"
    if not runtime.is_file():
        raise CompatError("BakaSU legacy init.rc/ksud runtime is missing")
    runtime_text = strip_comments(runtime.read_text())
    if any(sym not in runtime_text for sym in ("KERNEL_SU_RC", "KSUD_PATH", "ksu_is_init_rc_hook_enabled")):
        raise CompatError("BakaSU legacy init.rc/ksud runtime has changed; review this profile")

    destination = common / "include/linux" / HEADER
    if destination.exists() and destination.read_text() != header:
        raise CompatError(f"{destination}: does not match the selected BakaSU source")
    updated = source if INCLUDE in source else source.replace(anchor, anchor + BRIDGE, 1)
    changed = updated != source or not destination.exists()
    if check_only:
        if changed:
            raise CompatError("BakaSU compatibility bridge has not been installed")
        return False
    # Validate everything first, then write only the two intended files.
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(header)
    if updated != source:
        exec_path.write_text(updated)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ksu", type=Path)
    parser.add_argument("common", type=Path)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()
    try:
        changed = install(args.ksu, args.common, args.check)
    except (CompatError, OSError) as exc:
        print(f"::error title=BakaSU/SUSFS::{exc}")
        return 1
    print("BakaSU/SUSFS bridge: " + ("installed" if changed else "verified"))
    print("init mode: legacy init.rc/ksud; new KernelSU preinit runner explicitly DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
