#!/usr/bin/env python3
"""检查 SUSFS 内核补丁需要的外部符号，当前 KernelSU 源码是否都提供了。

用法:
  susfs_ksu_check.py <SUSFS kernel_patches 目录> <KernelSU/kernel 目录> [内核 common 目录]

SUSFS 的 50_add_susfs_in_gki-*.patch 会在内核里用 extern 声明并调用 KernelSU 侧的函数/变量
（例如 ksu_handle_execveat、ksu_selinux_hide_running）。SUSFS 跟随官方 KernelSU 主线更新后，
可能要求新的符号（例如 2026-10-19 的 5a3af83 / e24d1726 起需要 ksu_setup_preinit_file、
my_setprocattr、my_write_context、my_write_access），而 BakaSU / SukiSU-Ultra 还没有提供或只是
static 函数，此时内核能打上补丁，却会在最后链接时报 undefined reference，白白浪费一次完整编译。

本脚本在打补丁前做静态检查：
  1. 收集补丁新增行里所有 extern 声明的符号；
  2. 去掉 SUSFS 自己定义的（补丁新增行、kernel_patches/fs、include 里的定义）；
  3. 剩下的必须在 KernelSU 源码中有非 static 定义；KernelSU 里没有的，再到内核 common 中找
     （内核自身提供的符号）。
全部满足返回 0；有缺失返回 1 并列出缺失的符号；参数或目录错误返回 2。
这只是接口（链接）层面的检查，不能代替编译和实机验证。
"""
import argparse
import re
import sys
from pathlib import Path

from bakasu_susfs_compat import CompatError, guarded_preinit_lines, load_profile

IDENT = r"[A-Za-z_]\w*"
# 声明中可能出现在变量名后面的修饰
VAR_SUFFIX = r"(?:\s+__(?:read_mostly|ro_after_init|initdata|weak)\b|\s*\[[^\]]*\])*"
KEYWORDS = {"const", "volatile", "struct", "union", "enum", "unsigned", "signed",
            "static", "inline", "extern", "__read_mostly", "__ro_after_init"}


def added_lines(patch_text: str) -> list:
    out = []
    for line in patch_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            out.append(line[1:])
    return out


def extern_symbols(lines: list) -> set:
    """补丁新增代码里 extern 声明的符号名（支持跨行声明）。"""
    syms, buf = set(), ""
    for line in lines:
        s = re.sub(r"//.*", "", line).strip()
        if not buf and not re.match(r"extern\b", s):
            continue
        if re.match(r'extern\s+"C"', s):
            continue
        buf += " " + s
        if ";" not in buf:
            continue
        decl = buf.split(";", 1)[0]
        buf = ""
        decl = re.sub(r"__attribute__\s*\(\(.*?\)\)", " ", decl)
        m = re.match(r"\s*extern\s+(.*?)\b(" + IDENT + r")\s*\(", decl)   # 函数
        if m and "(*" not in decl:
            syms.add(m.group(2))
            continue
        m = re.search(r"\b(" + IDENT + r")" + VAR_SUFFIX + r"\s*$", decl)  # 变量
        if m and m.group(1) not in KEYWORDS:
            syms.add(m.group(1))
    return syms


def _def_patterns(sym: str):
    e = re.escape(sym)
    head = r"^(?!\s)(?!extern\b)(?!#)(?!typedef\b)(?!return\b)"
    return [
        # 函数定义必须有函数体：接受跨行参数/单行函数，拒绝只有声明的多行原型。
        re.compile(head + r"([^;=(\n]*?)\b" + e + r"\s*\([^;{}]*\)\s*(?:#[^\n]*\n\s*)*\{", re.M),
        # 变量定义（行首，带初始化或直接 ;）
        re.compile(head + r"([^;(\n]*?)\b" + e + VAR_SUFFIX + r"\s*(=|;)", re.M),
        # DEFINE_STATIC_KEY_TRUE/FALSE(sym)、DEFINE_PER_CPU(type, sym) 等（可能缩进在 #ifdef 块里）
        re.compile(r"^[ \t]*((?:\w+[ \t]+)*)DEFINE_\w+\((?:[^)\n]*,\s*)?" + e + r"\s*\)", re.M),
    ]


def strip_noise(text: str) -> str:
    """去掉注释和 __attribute__((...))，避免干扰行首定义的识别。"""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"__attribute__\s*\(\((?:[^()]|\([^()]*\))*\)\)\s*", "", text)
    return text


def find_definitions(sym: str, files: list) -> list:
    """返回 [(文件, 是否 static)]，只看行首定义。"""
    found = []
    pats = _def_patterns(sym)
    for path, text in files:
        if sym not in text:
            continue
        for pat in pats:
            for m in pat.finditer(text):
                prefix = m.group(1) or ""
                found.append((path, bool(re.search(r"\bstatic\b", prefix))))
    return found


def load_sources(root: Path, exts=(".c", ".h")) -> list:
    files = []
    for p in root.rglob("*"):
        if p.suffix in exts and p.is_file():
            try:
                files.append((p, strip_noise(p.read_text(errors="replace"))))
            except OSError:
                pass
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("susfs", type=Path)
    parser.add_argument("ksu", type=Path)
    parser.add_argument("common", nargs="?", type=Path)
    parser.add_argument("--bakasu-legacy-init", action="store_true",
                        help="require downstream profile v1; honor guarded KSU_NO_PREINIT blocks")
    args = parser.parse_args()
    susfs, ksu, common = args.susfs, args.ksu, args.common
    patches = sorted(susfs.glob("50_add_susfs_in_gki-*.patch"))
    if not patches:
        print(f"::error title=SUSFS check::{susfs} 下没有 50_add_susfs_in_gki-*.patch")
        return 2
    if not ksu.is_dir():
        print(f"::error title=SUSFS check::找不到 KernelSU 目录 {ksu}")
        return 2
    lines = []
    for p in patches:
        patch_lines = added_lines(p.read_text(errors="replace"))
        if args.bakasu_legacy_init:
            try:
                load_profile(ksu)
                patch_lines = guarded_preinit_lines(patch_lines)
            except (CompatError, OSError) as exc:
                print(f"::error title=SUSFS check::{exc}")
                return 1
        lines += patch_lines
    if args.bakasu_legacy_init:
        print("BakaSU profile v1: KSU_NO_PREINIT=1; legacy init.rc/ksud (NOT a preinit implementation)")
    wanted = extern_symbols(lines)

    # SUSFS 自己提供的定义：补丁新增行 + kernel_patches 下的源码（fs/susfs.c 等）
    susfs_files = [(Path("<patch>"), strip_noise("\n".join(lines)))]
    for sub in ("fs", "include"):
        if (susfs / sub).is_dir():
            susfs_files += load_sources(susfs / sub)
    ksu_files = load_sources(ksu, exts=(".c",))

    missing, static_only, from_ksu, from_kernel = [], [], [], []
    common_files = None
    for sym in sorted(wanted):
        if any(not st for _, st in find_definitions(sym, susfs_files)):
            continue
        defs = find_definitions(sym, ksu_files)
        if any(not st for _, st in defs):
            from_ksu.append(sym)
            continue
        if defs:
            static_only.append((sym, defs[0][0].relative_to(ksu)))
            continue
        if common is not None and common.is_dir():
            if common_files is None:
                common_files = load_sources(common, exts=(".c",))
            if any(not st for _, st in find_definitions(sym, common_files)):
                from_kernel.append(sym)
                continue
        missing.append(sym)

    print(f"SUSFS 补丁需要的外部符号: {len(wanted)} 个；KernelSU 提供 {len(from_ksu)} 个"
          + (f"，内核提供 {len(from_kernel)} 个" if from_kernel else ""))
    if not static_only and not missing:
        print("SUSFS ↔ KernelSU 接口检查通过")
        return 0
    for sym, path in static_only:
        print(f"  ✗ {sym}: KernelSU 中只有 static 定义（{path}），内核无法链接")
    for sym in missing:
        where = "KernelSU 和内核源码中都" if common is not None else "KernelSU 中"
        print(f"  ✗ {sym}: {where}没有定义")
    return 1


if __name__ == "__main__":
    sys.exit(main())
