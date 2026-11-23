"""Offline checks for native BakaSU + SUSFS SELinux integration. No network or kernel build.
Run: python3 -m unittest discover -s tests -v
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from susfs_feature_compat import plan

WF = ROOT / '.github/workflows/Build Kernel OnePlus.yml'
FLAG = 'CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER'
BRACED = ('    case CMD_SUSFS_SET_PRIORITY_UID_FILTER: {\n'
          '        susfs_set_priority_uid_filter(arg);\n'
          '        return 0;\n'
          '    }')


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class NativeBakaSUSusfsTests(unittest.TestCase):
    def test_local_bridge_is_retired(self):
        wf = WF.read_text()
        self.assertNotIn('bakasu_selinux_compat.py', wf)
        self.assertNotIn('bakasu-snapshot-bridge', wf)
        self.assertIn('SELINUX_BACKEND=bakasu-native-susfs-ledger', wf)
        self.assertFalse((ROOT / 'scripts/bakasu_selinux_compat.py').exists())
        self.assertFalse((ROOT / 'patches/bakasu').exists())
        self.assertFalse((ROOT / 'tests/fixtures/bakasu_selinux').exists())

    def run_guard(self, susfs_c, sepolicy):
        source = WF.read_text()
        a = source.index('            susfs_ok() {')
        b = source.index('\n            }\n', a) + len('\n            }\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / 'kernel_patches/fs/susfs.c', susfs_c)
            write(root / 'ksu/selinux/sepolicy.c', sepolicy)
            fake = root / 'bin/python3'
            write(fake, '#!/bin/sh\nexit 0\n')
            fake.chmod(0o755)
            script = textwrap.dedent(source[a:b]) + '\nsusfs_ok\n'
            return subprocess.run(
                ['bash', '-euo', 'pipefail', '-c', script], cwd=tmp, text=True, capture_output=True,
                env={**os.environ, 'PATH': str(root / 'bin') + os.pathsep + os.environ['PATH'],
                     'IS_RESUKISU': 'true', 'KSU_SRC': str(root / 'ksu'),
                     'COMMON_SRC': tmp, 'GITHUB_WORKSPACE': tmp})

    def test_native_registration_is_accepted(self):
        result = self.run_guard('int susfs_add_sus_type(const char *c, u32 v) { return 0; }\n',
                                '    susfs_add_sus_type(type_name, type->value);\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bakasu_without_native_registration_fails_closed(self):
        result = self.run_guard('int susfs_add_sus_type(const char *c, u32 v) { return 0; }\n',
                                'extern int susfs_add_sus_type(const char *secctx, u32 type_value);\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('没有原生注册', result.stdout)

    def test_legacy_susfs_without_ledger_is_not_blocked(self):
        result = self.run_guard('/* legacy susfs */\n', '/* legacy bakasu */\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def feature_tree(self, root, guarded):
        sus, ksu = root / 'sus', root / 'ksu'
        write(sus / 'fs/susfs.c', '#ifdef ' + FLAG + '\nvoid susfs_set_priority_uid_filter(void __user *arg) {}\n#endif\n')
        write(sus / 'include/linux/susfs.h', '#ifdef ' + FLAG + '\nvoid susfs_set_priority_uid_filter(void __user *arg);\n#endif\n')
        body = ('#ifdef ' + FLAG + '\n' + BRACED + '\n#endif // ' + FLAG + '\n') if guarded else (BRACED + '\n')
        write(ksu / 'supercall/dispatch.c', 'switch (cmd) {\n' + body + '}\n')
        write(ksu / 'Kconfig', 'config KSU_SUSFS_PRIORITY_UID_FILTER\n\tbool "priority"\n\tdepends on KSU_SUSFS\n\tdefault y\n\n'
                               'config KSU_SUSFS_SUS_MAP\n\tbool "map"\nendmenu\n')
        return sus, ksu

    def test_native_upstream_priority_layout_needs_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(plan(*self.feature_tree(Path(tmp), guarded=True)), {})

    def test_unguarded_braced_priority_block_is_wrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus, ksu = self.feature_tree(Path(tmp), guarded=False)
            changes = plan(sus, ksu)
            self.assertIn('#ifdef ' + FLAG + '\n' + BRACED + '\n#endif', changes[ksu / 'supercall/dispatch.c'])


class PriorityIoctlFormTests(unittest.TestCase):
    def test_bare_and_brace_forms_are_recognised(self):
        import susfs_feature_compat
        bare = '    case CMD_SUSFS_SET_PRIORITY_UID_FILTER:\n        susfs_set_priority_uid_filter(arg);\n        return 0;'
        self.assertEqual(susfs_feature_compat.CALL.search(bare).group(0), bare)
        self.assertEqual(susfs_feature_compat.CALL.search(BRACED).group(0), BRACED)

    def test_unbalanced_brace_form_is_rejected(self):
        import susfs_feature_compat
        broken = '    case CMD_SUSFS_SET_PRIORITY_UID_FILTER: {\n        susfs_set_priority_uid_filter(arg);\n        return 0;\n'
        self.assertIsNone(susfs_feature_compat.CALL.search(broken))


if __name__ == '__main__':
    unittest.main()
