"""Execute pinned-manager pairing shell with fake CI artifacts, without network/APK tools."""
import tempfile
from pathlib import Path
import unittest

from test_bakasu_pin import bash, step_script


class SukiManagerTests(unittest.TestCase):
    def pair(self, uapi='6', artifact='yes', run='yes', version='42424'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            makefile = root / 'kernel_workspace/kernel_platform/KernelSU/kernel/Makefile'
            makefile.parent.mkdir(parents=True)
            makefile.write_text('KSU_VERSION     := 40000\n')
            dest = root / 'env'
            dest.touch()
            mocks = r'''
            gh() {
              case "$*" in
                *'/contents/uapi/supercall.h?'*) printf 'static const int KERNEL_SU_UAPI_VERSION = %s;\n' "$MOCK_UAPI" ;;
                *'/actions/workflows/'*) [[ "$MOCK_RUN" == no ]] || printf '123\n' ;;
                *'/artifacts?'*) [[ "$MOCK_ARTIFACT" == no ]] || printf 'https://example.invalid/fixture\n' ;;
                *) echo 'Unexpected request' >&2; return 1 ;;
              esac
              return 0
            }
            curl() { return 0; }
            unzip() { printf 'fixture APK' > "${@: -1}/manager-arm64-v8a-release.apk"; }
            python3() { printf '%s\n' "$MOCK_VERSION"; }
            '''
            result = bash(mocks + step_script('Pair SukiSU-Ultra Manager'), dict(
                GITHUB_WORKSPACE=tmp, RUNNER_TEMP=tmp, GITHUB_TOKEN='fixture',
                GITHUB_ENV=str(dest), MANAGER_REPO='SukiSU-Ultra/SukiSU-Ultra',
                MANAGER_SHA='a' * 40, KSU_UAPI='6', MOCK_UAPI=uapi, MOCK_RUN=run,
                MOCK_ARTIFACT=artifact, MOCK_VERSION=version), cwd=tmp)
            return result, makefile.read_text(), dest.read_text()

    def test_matching_pinned_manager_binds_version(self):
        result, makefile, env = self.pair()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('KSU_VERSION     := 42424', makefile)
        self.assertIn('KSUVER=42424', env)

    def test_wrong_uapi_stops_before_changing_kernel_version(self):
        result, makefile, env = self.pair(uapi='5')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(makefile, 'KSU_VERSION     := 40000\n')
        self.assertEqual(env, '')

    def test_missing_ci_or_artifact_stops(self):
        for option in ({'run': 'no'}, {'artifact': 'no'}):
            result, _, env = self.pair(**option)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(env, '')

    def test_invalid_apk_version_stops(self):
        result, _, env = self.pair(version='invalid')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(env, '')

    def test_no_release_or_floating_main_fallback(self):
        source = step_script('Pair SukiSU-Ultra Manager')
        self.assertNotIn('/releases', source)
        self.assertNotIn('branch=main', source)
        self.assertIn('head_sha=${MANAGER_SHA}', source)
        self.assertIn('.head_sha == \\"$MANAGER_SHA\\"', source)


if __name__ == '__main__':
    unittest.main()
