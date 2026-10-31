"""Regression coverage for official BakaSU/SUSFS October 2026 update."""
import unittest
from pathlib import Path
import tempfile
import textwrap

from test_susfs_auto import make_susfs, write, run_check
from test_bakasu_pin import WF, bash

ROOT = Path(__file__).resolve().parents[1]
BAKA = '5785bdb8091304322f597f67d50e0b79f9815cb2'
SUSFS = '8930474a298d07ab9f1beca926779cbc3656b79e'
LEGACY = '31eb14add587b0a089dfe1819f92cc94920e141e'
CONTRACT = '''ifeq ($(shell grep -q "ksu_selinux_hide_running" $(srctree)/security/selinux/hooks.c; echo $$?),0)
$(info -- BakaSU/susfs_feature_check: selinux_hide manual hook found)
ccflags-y += -DKSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE
endif
'''


class BakaSUAliasTests(unittest.TestCase):
    def check_alias(self, static=False, contract=True, hook=True, definition=True, conditional=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            declarations = 'extern int my_setprocattr(const char *name, void *value, size_t size);\n'
            if hook:
                declarations += 'extern bool ksu_selinux_hide_running __read_mostly;\n'
            kp = make_susfs(root / 'susfs', declarations)
            code = ('#ifdef KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE\n' if conditional else '')
            code += '    #define ksu_handle_selinux_setprocattr my_setprocattr\n'
            if conditional:
                code += '#else\n/* original hook setup */\n#endif\n'
            if definition:
                code += ('static ' if static else '') + 'int __nocfi ksu_handle_selinux_setprocattr(const char *name, void *value, size_t size)\n{\n return 0;\n}\n'
            if hook:
                code += 'bool ksu_selinux_hide_running __read_mostly = false;\n'
            write(root / 'ksu/feature/selinux_hide.c', code)
            if contract:
                write(root / 'ksu/tools/susfs_compat.mk', CONTRACT)
            return run_check(kp, root / 'ksu')

    def test_audited_upstream_alias_with_contract_is_accepted(self):
        r = self.check_alias()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_alias_does_not_make_static_function_linkable(self):
        self.assertEqual(self.check_alias(static=True).returncode, 1)

    def test_alias_without_kbuild_contract_is_rejected(self):
        self.assertEqual(self.check_alias(contract=False).returncode, 1)

    def test_alias_without_selected_susfs_hook_is_rejected(self):
        self.assertEqual(self.check_alias(hook=False).returncode, 1)

    def test_alias_without_real_definition_is_rejected(self):
        self.assertEqual(self.check_alias(definition=False).returncode, 1)

    def test_unknown_macro_layout_is_not_blindly_expanded(self):
        self.assertEqual(self.check_alias(conditional=False).returncode, 1)


class UpdatedPinTests(unittest.TestCase):
    def source_floor(self, baka=True, sha=None):
        expected = BAKA if baka else 'b16e899a555e9b96aa1225f049cd7274820ca5b8'
        sha = sha or expected
        source = WF.read_text()
        a = source.index('            STABLE_SUSFS_COMMIT=')
        b = source.index('            SUSFS_AUTO=false', a)
        code = textwrap.dedent(source[a:b])
        r = bash(code + '\nprintf "%s" "$STABLE_SUSFS_COMMIT"',
                 {'IS_RESUKISU': 'true' if baka else 'false', 'KSU_SHA': sha, 'KSU_PINNED': 'true' if sha == expected else 'false'})
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_modern_bakasu_floor_includes_uaf_fix(self):
        self.assertEqual(self.source_floor(), SUSFS)

    def test_latest_sukisu_uses_modern_floor(self):
        self.assertEqual(self.source_floor(baka=False), SUSFS)

    def test_explicit_legacy_bakasu_rollback_keeps_old_floor(self):
        self.assertEqual(self.source_floor(sha='5b76b884c75f729a220bb317aa4a4fc78f0e0e9c'), LEGACY)

    def test_anykernel_beta_and_bbg_pins_are_documented(self):
        source = WF.read_text()
        for sha in ['47f23f7ece3ef212a392ec9ea5466e5f0b55d3c7',
                    '028ff7fd509e2104596da7cc1ef8e6ce2a0c9082']:
            self.assertIn(sha, source)
            for name in ['README.md', 'README-en.md']:
                self.assertIn(sha[:8], (ROOT / name).read_text())
        self.assertIn('PRE="--prerelease"', source.split('# AnyKernel3 v31.0 beta', 1)[1])

    def test_no_dependency_on_deleted_test_branch_or_old_fork(self):
        source = WF.read_text()
        self.assertNotIn('test/bakasu-latest-susfs', source)
        self.assertNotIn('suhuli/BakaSU', source)
        self.assertIn('Baka-SU/BakaSU', source)



if __name__ == '__main__':
    unittest.main()
