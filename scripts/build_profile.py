#!/usr/bin/env python3
"""Resolve one of three reviewed, pinned build profiles; never accept arbitrary refs."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('BAKASU', 'SUKISU', 'SUKISU_KPM')


def resolve(profile, versions=None):
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
    return {
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


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: build_profile.py PROFILE')
    try:
        env = resolve(sys.argv[1])
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
