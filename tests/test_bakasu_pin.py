"""Offline regression tests for BakaSU pin/manager selection. No network or kernel build.
Run: python3 -m unittest discover -s tests -v
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/Build Kernel OnePlus.yml'
PIN = '5b76b884c75f729a220bb317aa4a4fc78f0e0e9c'
OLD = '239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb'
SUKI = '6c284e957feaa9a388a9f1c37dc4ec80d95e434b'


def step_script(name):
    source = WF.read_text()
    block = source.split('      - name: ' + name + '\n', 1)[1]
    block = block.split('\n      - name:', 1)[0]
    script = block.split('        run: |\n', 1)[1]
    return textwrap.dedent(script)


def bash(script, env=None, cwd=None):
    return subprocess.run(['bash', '-euo', 'pipefail', '-c', script],
                          text=True, capture_output=True, cwd=cwd,
                          env={**os.environ, **(env or {})})


class BakaSUPinTests(unittest.TestCase):
    def selection(self, user='', manual='', is_baka='true'):
        source = WF.read_text()
        a = source.index('          EXPECT_COMMIT=""')
        b = source.index('          echo "KernelSU:', a)
        script = textwrap.dedent(source[a:b])
        variables = dict(USER_BRANCH=user, MANUAL_HASH=manual,
                         IS_RESUKISU=is_baka, RESUKISU_TAG='v4.2.0-rc3',
                         RESUKISU_COMMIT=PIN, SUKISU_BUILTIN_COMMIT=SUKI)
        result = bash(script + '\nprintf "%s|%s" "$KSU_REF" "$EXPECT_COMMIT"', variables)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_default_uses_commit_not_release_tag(self):
        self.assertEqual(self.selection(), PIN + '|' + PIN)

    def test_custom_branch_remains_supported(self):
        self.assertEqual(self.selection(user='main'), 'origin/main|')

    def test_explicit_rollback_overrides_default(self):
        self.assertEqual(self.selection(manual=OLD), OLD + '|')

    def test_hash_has_priority_over_branch(self):
        self.assertEqual(self.selection(user='main', manual=OLD), OLD + '|')

    def test_sukisu_pin_is_unchanged(self):
        self.assertEqual(self.selection(is_baka='false'), SUKI + '|' + SUKI)

    def release_flag(self, actual):
        source = WF.read_text()
        a = source.index('          if [[ "$IS_RESUKISU" == true && "$ACTUAL_COMMIT" == "$RESUKISU_RELEASE_COMMIT" ]]')
        b = source.index('\n          fi', a) + len('\n          fi')
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'env'; dest.touch()
            result = bash(textwrap.dedent(source[a:b]), dict(
                IS_RESUKISU='true', ACTUAL_COMMIT=actual,
                RESUKISU_RELEASE_COMMIT=OLD, RESUKISU_TAG='v4.2.0-rc3',
                GITHUB_ENV=str(dest)))
            self.assertEqual(result.returncode, 0, result.stderr)
            return dest.read_text()

    def test_default_never_selects_old_release_apk(self):
        self.assertEqual(self.release_flag(PIN), '')

    def test_old_source_can_use_matching_release_apk(self):
        self.assertEqual(self.release_flag(OLD), 'RESUKISU_RELEASE=v4.2.0-rc3\n')

    def run_manager(self, version, artifact='yes'):
        # Mock network and APK decoding only; execute actual workflow shell logic.
        mocks = r'''
        gh() {
          case "$*" in
            *'/actions/workflows/'*) printf '37924502987\n' ;;
            *'/artifacts?'*) if [[ "$MOCK_ARTIFACT" == yes ]]; then printf 'https://test.invalid/artifact\n'; fi ;;
            *) echo 'Unexpected gh call' >&2; return 1 ;;
          esac
        }
        curl() { return 0; }
        unzip() {
          local dest="${@: -1}"
          printf 'mock APK' > "$dest/BakaSU-arm64-v8a-release.apk"
        }
        python3() { printf '%s\n' "$MOCK_VERSION"; }
        '''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'AnyKernel3').mkdir()
            script = step_script('Download Manager APK')
            script = script.replace('${{ steps.manager.outputs.manager_artifact }}', 'Manager-release')
            script = script.replace('${{ steps.manager.outputs.manager_repo }}', 'Baka-SU/BakaSU')
            result = bash(textwrap.dedent(mocks) + script, dict(
                IS_RESUKISU='true', KSU_SHA=PIN, KSUVER='35222',
                GITHUB_WORKSPACE=tmp, GITHUB_TOKEN='mock-not-a-real-token',
                MOCK_VERSION=version, MOCK_ARTIFACT=artifact), cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            return list((root / 'AnyKernel3').glob('*.apk')), result.stdout

    def test_matching_manager_is_attached(self):
        files, output = self.run_manager('35222')
        self.assertEqual(len(files), 1, output)

    def test_wrong_manager_is_not_attached(self):
        files, output = self.run_manager('35180')
        self.assertEqual(files, [], output)
        self.assertIn('拒绝附带', output)

    def test_missing_manager_is_not_replaced_with_old_release(self):
        files, output = self.run_manager('35222', artifact='no')
        self.assertEqual(files, [], output)
        self.assertIn('本次不附带管理器', output)

    def test_upstream_susfs_block_is_preserved(self):
        script = WF.read_text()
        self.assertIn('Please wait susfs update', script)
        self.assertNotRegex(script, r'sed[^\n]*(?:/d|s/)[^\n]*Please wait')
        pattern = r'^[[:space:]]*\$\(error[[:space:]]+Please wait susfs update\.'
        found = subprocess.run(['grep', '-qE', pattern],
            input='$(error Please wait susfs update.)\n', text=True)
        self.assertEqual(found.returncode, 0)

    def test_version_detection_accepts_bakasu_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'build.log').write_text('-- BakaSU version code: 35222\n-- BakaSU version name: v4.2.0-rc3-5b76b884@BakaSU\n')
            dest = root / 'env'; dest.touch()
            result = bash(step_script('Detect KSU Version'), dict(
                GITHUB_WORKSPACE=tmp, GITHUB_ENV=str(dest), KSUVER='35222'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('KSUVER=35222', dest.read_text())
            self.assertIn('KSU_NAME=v4.2.0-rc3-5b76b884@BakaSU', dest.read_text())

    def test_manager_ci_requires_exact_head_sha(self):
        self.assertIn('.head_sha == \\"$KSU_SHA\\"', step_script('Download Manager APK'))


if __name__ == '__main__':
    unittest.main()
