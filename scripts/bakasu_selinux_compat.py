#!/usr/bin/env python3
"""BakaSU SELinux backend selection for SUSFS android12-5.10.

Two reviewed modes, chosen from the BakaSU source layout:

* native (BakaSU >= 0799a678 / 2b558ca5): upstream populates the SUSFS type/AV
  ledgers from selinux/sepolicy.c (susfs_add_sus_type /
  susfs_add_sus_avd_allowed_by_type) and builds feature/selinux_hide/
  selinux_hide_susfs.c when the SUSFS manual hook is present. The SUSFS kernel
  patch is used unmodified; nothing is patched here.
* bridge (older BakaSU with feature/selinux_hide.c, e.g. 7b65bde0): the audited
  snapshot backend bridge routes the three SUSFS manual hooks to BakaSU's
  my_write_context / my_write_access / my_setprocattr.

Unknown layouts fail closed. No mutation in --check. Under GitHub Actions the
selected backend label is written to $GITHUB_ENV as SELINUX_BACKEND.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

PATCH = Path(__file__).resolve().parents[1] / 'patches/bakasu/0001-susfs-selinux-snapshot-backend.patch'
CONTRACT = {
    'feature/selinux_hide.c': '802cb44b9e2d59ca4de2517ceeb290fdcca050fec599b8e3f7eee52f193e50e7',
    'tools/susfs_compat.mk': 'fed05d93c03f11e252ff3fc411e0f2591059579ec0be8c32ab6b83bbd6a1d91e',
    'selinux/rules.c': 'd599f97877dcff4a59201ca32dd9f765f734823d043b9569504f6eb66397b2e5',
}
SUSFS_PATCH = '50_add_susfs_in_gki-android12-5.10.patch'
# Both layouts are covered by exact-source OEM patch regression fixtures.
SUSFS_HASHES = {
    'f17439344475ae8ae91b80c46a14e87c475db2a6a396cf6adfe142f1ee6a8b74',  # 5436438b
    'bc7b152944cf13384f17238df43fc3c97025c254b61e47afb9864cca1051e041',  # 784ac9e6
}
BRIDGE_LABEL = 'bakasu-snapshot-bridge-v1'
NATIVE_LABEL = 'bakasu-native-susfs-ledger'
BRIDGE_MARKERS = ('return my_setprocattr(', 'return my_write_context(',
                  'return my_write_access(', 'extern int my_setprocattr(')
LEDGER_FUNCS = ('susfs_add_sus_type', 'susfs_add_sus_avd_allowed_by_type')


def _calls(text, func):
    """Real call sites (not extern declarations) of func."""
    return [m for m in re.finditer(r'^(?![ \t]*extern\b)[^\n]*\b' + func + r'\s*\(', text, re.M)]


def is_native(ksu):
    """True only for the reviewed upstream native layout; never guess."""
    ksu = Path(ksu)
    sepolicy = ksu / 'selinux/sepolicy.c'
    if (ksu / 'feature/selinux_hide.c').exists() or not sepolicy.exists():
        return False
    if not (ksu / 'feature/selinux_hide/selinux_hide_susfs.c').exists():
        return False
    text = sepolicy.read_text(errors='replace')
    return all(len(_calls(text, f)) >= 1 for f in LEDGER_FUNCS)


def validate_native(susfs, ksu):
    susfs, ksu = Path(susfs), Path(ksu)
    main = (ksu / 'feature/selinux_hide/selinux_hide.c').read_text(errors='replace')
    if not re.search(r'#ifdef KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE\s*\n#include "selinux_hide_susfs\.c"', main):
        raise ValueError('unreviewed BakaSU native SELinux layout: selinux_hide_susfs.c selection missing')
    mk = (ksu / 'tools/susfs_compat.mk').read_text(errors='replace')
    if 'ksu_selinux_hide_running' not in mk or 'KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE' not in mk:
        raise ValueError('unreviewed BakaSU native SELinux layout: manual hook detection missing')
    fs = (susfs / 'fs/susfs.c').read_text(errors='replace')
    for func in LEDGER_FUNCS:
        if not re.search(r'^int ' + func + r'\s*\(', fs, re.M):
            raise ValueError(f'selected SUSFS has no ledger function {func}; native BakaSU needs it')
    patch = (susfs / SUSFS_PATCH).read_text(errors='replace')
    if 'ksu_selinux_hide_running' not in patch:
        raise ValueError('selected SUSFS patch has no SELinux manual hook; native backend unreviewed')
    if any(m in patch for m in BRIDGE_MARKERS):
        raise ValueError('selected SUSFS patch already routes to BakaSU snapshot helpers; review required')


def validate(susfs, ksu):
    """Return the selected mode ('native' or 'bridge'); raise if unreviewed."""
    if is_native(ksu):
        validate_native(susfs, ksu)
        return 'native'
    susfs, ksu = Path(susfs), Path(ksu)
    for name, expected in CONTRACT.items():
        path = ksu / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'unreviewed BakaSU SELinux contract: {name}')
    if hashlib.sha256((susfs / SUSFS_PATCH).read_bytes()).hexdigest() not in SUSFS_HASHES:
        raise ValueError('unreviewed SUSFS SELinux patch; review new upstream before building')
    return 'bridge'


def patch_run(common, reverse=False, dry=True):
    cmd = ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1',
           '-R' if reverse else '--forward']
    if reverse:
        cmd.append('--force')
    if dry:
        cmd.append('--dry-run')
    return subprocess.run(cmd, cwd=common, input=PATCH.read_text(),
                          text=True, capture_output=True)


def verify(common):
    for name, funcs in {
        'hooks.c': ['my_setprocattr(name, value, size)'],
        'selinuxfs.c': ['my_write_context(file, buf, size)', 'my_write_access(file, buf, size)'],
    }.items():
        text = (Path(common) / 'security/selinux' / name).read_text()
        for f in funcs:
            if text.count('return ' + f + ';') != 1:
                raise ValueError(f'missing/duplicate snapshot hook: {f}')
        if 'ksu_selinux_hide_running' not in text or 'current_uid().val >= 10000' not in text:
            raise ValueError('manual hook eligibility guard missing')
    if patch_run(common, reverse=True).returncode:
        raise ValueError('patched source differs from reviewed bridge')


def verify_native(common):
    """Native mode keeps the SUSFS kernel patch untouched: no bridge routes."""
    texts = [(Path(common) / 'security/selinux' / n).read_text() for n in ('hooks.c', 'selinuxfs.c')]
    if not any('ksu_selinux_hide_running' in t for t in texts):
        raise ValueError('SUSFS SELinux manual hook missing from kernel sources')
    for t in texts:
        for marker in BRIDGE_MARKERS:
            if marker in t:
                raise ValueError('snapshot bridge routes found in a native BakaSU build: ' + marker)


def record(label):
    env = os.environ.get('GITHUB_ENV')
    if env:
        with open(env, 'a') as f:
            f.write(f'SELINUX_BACKEND={label}\n')


def apply(susfs, ksu, common):
    if validate(susfs, ksu) == 'native':
        verify_native(common)
        record(NATIVE_LABEL)
        return 'native upstream ledger backend, bridge not applied'
    if patch_run(common, reverse=True).returncode == 0:
        verify(common)
        record(BRIDGE_LABEL)
        return 'already applied'
    result = patch_run(common)
    if result.returncode:
        raise ValueError('bridge dry-run failed: ' + result.stdout + result.stderr)
    result = patch_run(common, dry=False)
    if result.returncode:
        raise ValueError('bridge application failed: ' + result.stdout + result.stderr)
    verify(common)
    record(BRIDGE_LABEL)
    return 'applied'


if __name__ == '__main__':
    try:
        if len(sys.argv) == 4 and sys.argv[1] == '--check':
            mode = validate(*sys.argv[2:])
            if mode == 'native':
                print('BakaSU SELinux source contract accepted: native SUSFS ledger backend, no bridge')
            else:
                print('BakaSU SELinux source contract accepted; bridge must be applied after SUSFS patch')
        elif len(sys.argv) == 5 and sys.argv[1] == '--apply':
            print('BakaSU SELinux backend: ' + apply(*sys.argv[2:]))
        else:
            raise ValueError('usage: --check <kernel_patches> <ksu/kernel> | --apply <kernel_patches> <ksu/kernel> <common>')
    except (OSError, ValueError) as exc:
        sys.exit('::error title=BakaSU SELinux compatibility::' + str(exc))
