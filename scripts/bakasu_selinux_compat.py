#!/usr/bin/env python3
"""Audited BakaSU snapshot backend bridge for SUSFS android12-5.10.

This is not a ledger-population adapter. Keep BakaSU's existing snapshot lifetime,
permission checks and enable/running semantics; route all three manual hooks to
that backend. Unknown upstream sources fail closed. No mutation in --check.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

PATCH = Path(__file__).resolve().parents[1] / 'patches/bakasu/0001-susfs-selinux-snapshot-backend.patch'
CONTRACT = {
    'feature/selinux_hide.c': '802cb44b9e2d59ca4de2517ceeb290fdcca050fec599b8e3f7eee52f193e50e7',
    'tools/susfs_compat.mk': 'fed05d93c03f11e252ff3fc411e0f2591059579ec0be8c32ab6b83bbd6a1d91e',
    'selinux/rules.c': 'd599f97877dcff4a59201ca32dd9f765f734823d043b9569504f6eb66397b2e5',
}
SUSFS_PATCH = '50_add_susfs_in_gki-android12-5.10.patch'
SUSFS_HASH = 'f17439344475ae8ae91b80c46a14e87c475db2a6a396cf6adfe142f1ee6a8b74'


def validate(susfs, ksu):
    susfs, ksu = Path(susfs), Path(ksu)
    for name, expected in CONTRACT.items():
        if hashlib.sha256((ksu / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'unreviewed BakaSU SELinux contract: {name}')
    if hashlib.sha256((susfs / SUSFS_PATCH).read_bytes()).hexdigest() != SUSFS_HASH:
        raise ValueError('unreviewed SUSFS SELinux patch; review new upstream before building')


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


def apply(susfs, ksu, common):
    validate(susfs, ksu)
    if patch_run(common, reverse=True).returncode == 0:
        verify(common)
        return 'already applied'
    result = patch_run(common)
    if result.returncode:
        raise ValueError('bridge dry-run failed: ' + result.stdout + result.stderr)
    result = patch_run(common, dry=False)
    if result.returncode:
        raise ValueError('bridge application failed: ' + result.stdout + result.stderr)
    verify(common)
    return 'applied'


if __name__ == '__main__':
    try:
        if len(sys.argv) == 4 and sys.argv[1] == '--check':
            validate(*sys.argv[2:])
            print('BakaSU SELinux source contract accepted; bridge must be applied after SUSFS patch')
        elif len(sys.argv) == 5 and sys.argv[1] == '--apply':
            print('BakaSU SELinux snapshot bridge: ' + apply(*sys.argv[2:]))
        else:
            raise ValueError('usage: --check <kernel_patches> <ksu/kernel> | --apply <kernel_patches> <ksu/kernel> <common>')
    except (OSError, ValueError) as exc:
        sys.exit('::error title=BakaSU SELinux compatibility::' + str(exc))
