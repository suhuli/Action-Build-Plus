#!/usr/bin/env python3
"""Verify a kernel-only BakaSU fork can reuse its recorded upstream manager.

Usage: bakasu_manager_pair.py <BakaSU repository>
Prints JSON on success. No APK is substituted by version number alone: callers
must download the official artifact from the exact manager source commit.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from bakasu_susfs_compat import CompatError, load_profile


class PairingError(ValueError):
    pass


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
    if result.returncode:
        raise PairingError("git " + " ".join(args[:2]) + ": " + result.stderr.strip())
    return result.stdout.strip()


def inspect(root: Path) -> dict:
    load_profile(root / "kernel")
    base = (root / "kernel/tools/susfs_manager_commit").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise PairingError("susfs_manager_commit must contain a full upstream commit SHA")
    if git(root, "rev-parse", "--is-shallow-repository") != "false":
        raise PairingError("a full commit graph is required to calculate manager versionCode")
    if git(root, "rev-parse", base + "^{commit}") != base:
        raise PairingError("recorded upstream manager commit is not available")
    for path in ("manager", "userspace", "uapi"):
        if not (root / path).is_dir():
            raise PairingError(f"missing {path} source directory")
    changed = git(root, "diff", "--name-only", base, "--", "manager", "userspace", "uapi")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "--", "manager", "userspace", "uapi")
    if changed or untracked:
        raise PairingError("manager/userspace/UAPI differ from the pinned upstream manager; build and pair a new manager")
    kbuild = (root / "kernel/Kbuild").read_text()
    if ("KSU_VERSION_REF := $(shell cat $(KSU_SRC)/tools/susfs_manager_commit)" not in kbuild
            or "rev-list --count $(KSU_VERSION_REF)" not in kbuild):
        raise PairingError("Kbuild does not bind the SUSFS versionCode to the manager source commit")
    count = int(git(root, "rev-list", "--count", base))
    code = 30000 + count + 700
    if not 0 < code < 2**31:
        raise PairingError("invalid manager versionCode")
    uapi = (root / "uapi/supercall.h").read_text()
    version = re.search(r"KERNEL_SU_UAPI_VERSION\s*(?:=|,)\s*(\d+)", uapi)
    if not version:
        raise PairingError("cannot identify the unchanged UAPI version")
    return {
        "kernel_sha": git(root, "rev-parse", "HEAD"),
        "manager_repo": "Baka-SU/BakaSU",
        "manager_sha": base,
        "manager_version_code": code,
        "uapi_version": int(version.group(1)),
        "profile_version": 1,
        "init_mode": "legacy-initrc-no-preinit",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.root)
    except (CompatError, PairingError, OSError, ValueError) as exc:
        print(f"::error title=BakaSU manager pairing::{exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
