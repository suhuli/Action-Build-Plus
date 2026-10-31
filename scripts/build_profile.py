#!/usr/bin/env python3
"""Resolve reviewed defaults plus explicit, validated advanced overrides."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('BAKASU', 'SUKISU', 'SUKISU_KPM')


def resolve(profile, versions=None, options=None):
    if profile not in PROFILES:
        raise ValueError(f'Unknown PROFILE: {profile!r}; expected {", ".join(PROFILES)}')
    versions = versions if versions is not None else json.loads((ROOT / 'config/versions.json').read_text())
    for name, item in versions.items():
        if isinstance(item, dict) and not re.fullmatch(r'[0-9a-f]{40}', item.get('commit', '')):
            raise ValueError(f'{name}: expected a full, pinned commit SHA')
    if not re.fullmatch(r'[0-9a-f]{64}', versions['kpm']['patch_linux_sha256']):
        raise ValueError('KPM patch_linux must have a SHA-256 checksum')
    baka = profile == 'BAKASU'
    kernel = versions['bakasu' if baka else 'sukisu']
    result = {
        'BUILD_PROFILE': profile,
        'IS_BAKASU': str(baka).lower(),
        'KPM_ENABLED': str(profile == 'SUKISU_KPM').lower(),
        'MANAGER_REPO': kernel['repo'],
        'MANAGER_ARTIFACT': 'Manager-release' if baka else 'Manager',
        'MANAGER_SHA': kernel['commit'] if baka else versions['sukisu_manager']['commit'],
        'KSU_BRANCH': kernel['branch'],
        'KSU_COMMIT': kernel['commit'],
        'SUSFS_REPO': versions['susfs']['repo'],
        'SUSFS_BRANCH': versions['susfs']['branch'],
        'SUSFS_COMMIT': versions['susfs']['commit'],
        'SUKISU_PATCH_COMMIT': versions['kpm']['commit'],
        'KPM_PATCH_SHA256': versions['kpm']['patch_linux_sha256'],
        'AK3_COMMIT': versions['anykernel3']['commit'],
        'BBG_COMMIT': versions['bbg']['commit'],
    }

    options = options or {}
    def value(name, default=''):
        text = str(options.get(name, default)).strip()
        if '\n' in text or '\r' in text:
            raise ValueError(f'{name}: multiline value rejected')
        return text
    source = value('MANAGER_SOURCE', 'AUTO') or 'AUTO'
    sources = {'RESUKISU': (True, False), 'RESUKISU_SPOOF': (True, True),
               'SUKISU': (False, False), 'SUKISU_SPOOF': (False, True)}
    spoof = False
    if source != 'AUTO':
        if source not in sources:
            raise ValueError('Unknown MANAGER_SOURCE')
        baka, spoof = sources[source]
        kernel = versions['bakasu' if baka else 'sukisu']
    module = value('KPM', 'AUTO') or 'AUTO'
    if module == 'AUTO':
        module = 'KPM' if profile == 'SUKISU_KPM' and not baka else 'N/A'
    if module not in ('N/A', 'KPM', 'KPN'):
        raise ValueError('Unknown KPM implementation')
    if baka and module != 'N/A':
        raise ValueError('BakaSU does not support KPM/KPN; select SukiSU or N/A')
    meta = value('KSU_META', '//') or '//'
    parts = meta.rsplit('/', 2)
    if len(parts) != 3:
        raise ValueError('KSU_META must be branch/custom-label/commit; use // for defaults')
    branch, label, commit = parts
    if branch and (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', branch) or '..' in branch):
        raise ValueError('Invalid KSU_META branch name')
    if commit and not re.fullmatch(r'[0-9a-fA-F]{7,40}', commit):
        raise ValueError('KSU_META commit must be 7 to 40 hexadecimal characters')
    if label and not re.fullmatch(r'[A-Za-z0-9._+~-]+', label):
        raise ValueError('KSU_META custom label contains unsupported characters')
    custom = bool(branch or commit)
    susfs_meta = value('SUSFS_META')
    if susfs_meta and susfs_meta != '-1' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/~^+-]*', susfs_meta):
        raise ValueError('SUSFS_META must be -1, a rollback count, or a valid ref/commit')
    enabled = susfs_meta != '-1'
    if not baka and not enabled:
        raise ValueError('SukiSU builtin requires SUSFS for root; SUSFS_META=-1 is only allowed with BakaSU')
    dev = value('SUSFS_DEV', 'false').lower()
    if dev not in ('true', 'false'):
        raise ValueError('SUSFS_DEV must be true or false')
    susfs_branch = value('SUSFS_BRANCH') or versions['susfs']['branch']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', susfs_branch) or '..' in susfs_branch:
        raise ValueError('Invalid SUSFS branch')
    if dev == 'true' and not susfs_branch.endswith('-dev'):
        susfs_branch += '-dev'
    if not enabled:
        selection = 'disabled'
    elif susfs_meta:
        selection = 'manual'
    elif dev == 'true' or value('SUSFS_BRANCH'):
        selection = 'branch'
    elif custom:
        selection = 'compatible'  # Explicit kernel rollback: search compatible SUSFS, not for default builds.
    else:
        selection = 'pinned'
    result.update({
        'PRESET_PROFILE': profile,
        'BUILD_PROFILE': 'BAKASU' if baka else ('SUKISU_' + module if module != 'N/A' else 'SUKISU'),
        'IS_BAKASU': str(baka).lower(), 'MANAGER_SPOOF': str(spoof).lower(),
        'MODULE_MODE': module, 'KPM_ENABLED': str(module == 'KPM').lower(),
        'KPN_ENABLED': str(module == 'KPN').lower(),
        'MANAGER_REPO': kernel['repo'],
        'MANAGER_ARTIFACT': ('Spoofed-Manager-release' if spoof else 'Manager-release') if baka else ('Manager-spoofed' if spoof else 'Manager'),
        'MANAGER_SHA': kernel['commit'] if baka else versions['sukisu_manager']['commit'],
        'KSU_BRANCH': branch or kernel['branch'], 'KSU_COMMIT': kernel['commit'],
        'KSU_REF': commit or ('origin/' + branch if branch else kernel['commit']),
        'KSU_PINNED': str(not custom).lower(), 'CUSTOM_TAG': label,
        'SUSFS_ENABLED': str(enabled).lower(), 'SUSFS_SELECTION': selection,
        'SUSFS_META': susfs_meta, 'SUSFS_BRANCH': susfs_branch,
    })
    legacy = json.loads((ROOT / 'config/legacy.json').read_text())
    result['LEGACY_SUSFS_FLOOR'] = legacy['susfs_floor']
    result['BAKASU_RELEASE_COMMIT'] = legacy['bakasu_release']['commit']
    result['BAKASU_RELEASE_TAG'] = legacy['bakasu_release']['tag']
    return result


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: build_profile.py PROFILE')
    try:
        options = {key: os.environ.get('INPUT_' + key, default) for key, default in
                   [('MANAGER_SOURCE', 'AUTO'), ('KPM', 'AUTO'), ('KSU_META', '//'),
                    ('SUSFS_META', ''), ('SUSFS_BRANCH', ''), ('SUSFS_DEV', 'false')]}
        env = resolve(sys.argv[1], options=options)
        for key, value in env.items():
            if '\n' in value or '\r' in value:
                raise ValueError(f'{key}: multiline environment value rejected')
    except (ValueError, KeyError) as exc:
        sys.exit(f'::error title=Build profile::{exc}')
    with open(os.environ['GITHUB_ENV'], 'a') as output:
        output.writelines(f'{key}={value}\n' for key, value in env.items())
    print(f"Profile {env['BUILD_PROFILE']}: {env['MANAGER_REPO']}@{env['KSU_COMMIT'][:8]}, "
          f"SUSFS {env['SUSFS_COMMIT'][:8]}, KPM={env['KPM_ENABLED']}")


if __name__ == '__main__':
    main()
