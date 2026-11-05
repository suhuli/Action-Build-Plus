#!/usr/bin/env python3
"""Fail before compilation if selected BakaSU source no longer builds spoof APKs."""
from pathlib import Path
import sys

def check(path):
    source=Path(path).read_text()
    # Both the package customization and the advertised artifact must exist.
    return 'Spoofed-Manager' in source and 'KSU_PACKAGE_NAME' in source and 'spoofed' in source

if __name__ == '__main__':
    if len(sys.argv)!=2:
        sys.exit('usage: manager_variant_check.py <checked-out build-manager.yml>')
    if not check(sys.argv[1]):
        sys.exit('::error title=BakaSU Manager::所选源码的上游已取消伪装版管理器。请选择 RESUKISU 普通版；只有显式旧版且同提交仍提供伪装构建时才支持 RESUKISU_SPOOF。不替换成普通版或其他提交 APK。')
    print('Selected legacy source still advertises spoof manager builds; exact-commit artifact validation remains required.')
