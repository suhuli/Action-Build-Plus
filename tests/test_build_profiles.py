"""Exercise exactly three pinned profiles and real workflow shell with local fakes."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_bakasu_pin import WF, ROOT, bash, step_script

spec = importlib.util.spec_from_file_location('build_profile', ROOT / 'scripts/build_profile.py')
build_profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_profile)
VERSIONS = json.loads((ROOT / 'config/versions.json').read_text())


class ProfileTests(unittest.TestCase):
    def test_exactly_three_choices_and_default(self):
        text = WF.read_text()
        choices = text.split('        options:\n', 1)[1].split('      BUILD_TIME:', 1)[0]
        self.assertEqual([x.strip()[2:] for x in choices.splitlines() if x.strip()], list(build_profile.PROFILES))
        self.assertIn('default: BAKASU', text)

    def test_daily_bakasu_has_no_kpm(self):
        env = build_profile.resolve('BAKASU')
        self.assertEqual(env['IS_BAKASU'], 'true')
        self.assertEqual(env['KPM_ENABLED'], 'false')
        self.assertEqual(env['KSU_COMMIT'], VERSIONS['bakasu']['commit'])
        self.assertEqual(env['MANAGER_SHA'], env['KSU_COMMIT'])

    def test_sukisu_without_kpm(self):
        env = build_profile.resolve('SUKISU')
        self.assertEqual(env['IS_BAKASU'], 'false')
        self.assertEqual(env['KPM_ENABLED'], 'false')
        self.assertEqual(env['KSU_BRANCH'], 'builtin')
        self.assertEqual(env['MANAGER_SHA'], VERSIONS['sukisu_manager']['commit'])

    def test_kpm_is_only_enabled_for_sukisu_kpm(self):
        for profile in build_profile.PROFILES:
            self.assertEqual(build_profile.resolve(profile)['KPM_ENABLED'], str(profile == 'SUKISU_KPM').lower())

    def test_all_profiles_share_new_fixed_susfs(self):
        for profile in build_profile.PROFILES:
            self.assertEqual(build_profile.resolve(profile)['SUSFS_COMMIT'], VERSIONS['susfs']['commit'])

    def test_legacy_and_unknown_profiles_are_rejected(self):
        for value in ('RESUKISU', 'SUKISU_SPOOF', 'KPN', 'main', '', 'BAKASU\nKPM_ENABLED=true'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_profile.resolve(value)

    def test_moving_ref_is_rejected(self):
        versions = copy.deepcopy(VERSIONS)
        versions['bakasu']['commit'] = 'main'
        with self.assertRaises(ValueError):
            build_profile.resolve('BAKASU', versions)

    def test_missing_kpm_checksum_is_rejected(self):
        versions = copy.deepcopy(VERSIONS)
        versions['kpm']['patch_linux_sha256'] = ''
        with self.assertRaises(ValueError):
            build_profile.resolve('SUKISU_KPM', versions)

    def test_env_file_is_written_by_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'env'
            p = subprocess.run(['python3', str(ROOT / 'scripts/build_profile.py'), 'BAKASU'],
                               env={**os.environ, 'GITHUB_ENV': str(target)}, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('KPM_ENABLED=false\n', target.read_text())

    def test_old_input_entries_and_kpn_binaries_removed(self):
        text = WF.read_text()
        for name in ('MANAGER_SOURCE', 'KSU_META', 'SUSFS_META', 'SUSFS_DEV', 'KPM'):
            self.assertNotIn('      ' + name + ':\n', text)
            self.assertNotIn('github.event.inputs.' + name, text)
        for name in ('kptools-linux', 'kpimg-linux'):
            self.assertFalse((ROOT / 'patches' / name).exists())

    def test_documented_pins_match_manifest(self):
        for filename in ('README.md', 'README-en.md'):
            text = (ROOT / filename).read_text()
            for key, value in VERSIONS.items():
                if isinstance(value, dict):
                    self.assertIn(value['commit'], text, key)
            for profile in build_profile.PROFILES:
                self.assertIn(profile, text)


class PinnedSusfsTests(unittest.TestCase):
    def test_no_fallback_or_warn_and_continue(self):
        text = step_script('Apply SUSFS')
        for old in ('STABLE_SUSFS_COMMIT', 'git rev-list', 'SUSFS_AUTO', 'HEAD~', 'SUSFS_META'):
            self.assertNotIn(old, text)
        self.assertIn('"$SUSFS_COMMIT"', text)
        self.assertIn('susfs_fixups.py" pre .', text)
        self.assertIn('susfs_fixups.py" post .', text)
        self.assertIn('ksu_susfs_compat.py', text)

    def test_incompatible_fixed_susfs_stops_before_patching(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'kernel_workspace').mkdir()
            envfile = root / 'env'
            envfile.touch()
            env = {**build_profile.resolve('BAKASU'), 'GITHUB_WORKSPACE': tmp, 'GITHUB_ENV': str(envfile)}
            mocks = '''git() { if [[ "$*" == *rev-parse* ]]; then printf '%s' "$SUSFS_COMMIT"; fi; }
python3() { echo 'incompatible fixture'; return 1; }
patch() { echo 'MUST_NOT_PATCH'; return 0; }
'''
            script = step_script('Apply SUSFS').replace('${{ github.event.inputs.RE_KERNEL }}', 'false').replace('${{ env.KANDROID_VERSION }}', 'android12').replace('${{ env.KERNEL_VERSION }}', '5.10')
            result = bash(mocks + script, env, cwd=tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('MUST_NOT_PATCH', result.stdout)
            self.assertEqual(envfile.read_text(), '')


class KpmTests(unittest.TestCase):
    def run_tool(self, mode='success', checksum=True, profile='SUKISU_KPM'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            toolrepo = root / 'kernel_workspace/SukiSU_patch'
            (toolrepo / 'kpm').mkdir(parents=True)
            if mode == 'success':
                body = '#!/bin/sh\ncat Image > oImage\nprintf patched >> oImage\n'
            elif mode == 'unchanged':
                body = '#!/bin/sh\ncp Image oImage\n'
            elif mode == 'empty':
                body = '#!/bin/sh\n: > oImage\n'
            else:
                body = '#!/bin/sh\nexit 1\n'
            tool = toolrepo / 'kpm/patch_linux'
            tool.write_text(body)
            out = root / 'kernel_workspace/kernel_platform/out/Final-Image-Find'
            out.mkdir(parents=True)
            (out / 'Image').write_text('original')
            (root / 'AnyKernel3').mkdir()
            (root / 'AnyKernel3/Image').write_text('original')
            env = {**build_profile.resolve(profile), 'GITHUB_WORKSPACE': tmp,
                   'KPM_PATCH_SHA256': hashlib.sha256(body.encode()).hexdigest() if checksum else '0' * 64}
            mocks = '''git() { if [[ "$*" == *rev-parse* ]]; then printf '%s' "$SUKISU_PATCH_COMMIT"; fi; }
'''
            result = bash(mocks + step_script('Apply KPX and Replace Image'), env, cwd=tmp)
            return result, (root / 'AnyKernel3/Image').read_text()

    def test_valid_tool_replaces_image(self):
        result, image = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(image, 'originalpatched')

    def test_checksum_mismatch_stops(self):
        result, image = self.run_tool(checksum=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(image, 'original')

    def test_invalid_outputs_and_failure_do_not_replace_image(self):
        for mode in ('unchanged', 'empty', 'failed'):
            result, image = self.run_tool(mode)
            self.assertNotEqual(result.returncode, 0, mode)
            self.assertEqual(image, 'original')

    def test_bakasu_cannot_run_kpm_even_if_step_is_called(self):
        result, image = self.run_tool(profile='BAKASU')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(image, 'original')

    def test_job_step_is_guarded_by_profile(self):
        text = WF.read_text().split('      - name: Apply KPX and Replace Image\n', 1)[1]
        self.assertIn("if: ${{ env.KPM_ENABLED == 'true' }}", text.split('        run:', 1)[0])


if __name__ == '__main__':
    unittest.main()
