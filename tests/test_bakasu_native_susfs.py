"""Native BakaSU SUSFS SELinux backend selection. Synthetic layout, no kernel build."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bakasu_selinux_compat as compat  # noqa: E402
import susfs_feature_compat  # noqa: E402

MK = ('ifeq ($(shell grep -q "ksu_selinux_hide_running" $(srctree)/security/selinux/hooks.c; echo $$?),0)\n'
      '  $(info -- x)\n  ccflags-y += -DKSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE\nendif\n')
SEPOLICY = ('#ifdef CONFIG_KSU_SUSFS\n'
            'extern int susfs_add_sus_avd_allowed_by_type(u32 s_type, u32 t_type, u32 c_type, u32 orig_avd_allowed);\n'
            'extern int susfs_add_sus_type(const char *secctx, u32 type_value);\n#endif\n'
            'static void a(void)\n{\n    susfs_add_sus_avd_allowed_by_type(1, 2, 3, 4);\n}\n'
            'static void b(void)\n{\n    susfs_add_sus_type(name, 5);\n}\n')
HIDE = ('#ifdef KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE\n#include "selinux_hide_susfs.c"\n'
        '#else\n#include "selinux_hide_auto.c"\n#endif\n')
SUSFS_C = ('int susfs_add_sus_type(const char *secctx, u32 type_value)\n{\n\treturn 0;\n}\n'
           'int susfs_add_sus_avd_allowed_by_type(u32 s_type, u32 t_type, u32 c_type, u32 orig_avd_allowed)\n{\n\treturn 0;\n}\n')
PATCH = '+extern bool ksu_selinux_hide_running;\n+\treturn susfs_sel_write_access(file, buf, size);\n'


class NativeBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.ksu, self.sus, self.common = root / 'ksu', root / 'susfs', root / 'common'
        files = {
            self.ksu / 'tools/susfs_compat.mk': MK,
            self.ksu / 'selinux/sepolicy.c': SEPOLICY,
            self.ksu / 'feature/selinux_hide/selinux_hide.c': HIDE,
            self.ksu / 'feature/selinux_hide/selinux_hide_susfs.c': '// susfs mode\n',
            self.sus / 'fs/susfs.c': SUSFS_C,
            self.sus / compat.SUSFS_PATCH: PATCH,
            self.common / 'security/selinux/hooks.c': 'extern bool ksu_selinux_hide_running;\n',
            self.common / 'security/selinux/selinuxfs.c': 'return susfs_sel_write_access(file, buf, size);\n',
        }
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def snapshot(self):
        return {p: p.read_bytes() for p in Path(self.tmp.name).rglob('*') if p.is_file()}

    def test_native_layout_selected_without_bridge(self):
        self.assertTrue(compat.is_native(self.ksu))
        self.assertEqual(compat.validate(self.sus, self.ksu), 'native')

    def test_native_apply_does_not_patch_and_records_label(self):
        before = self.snapshot()
        env = Path(self.tmp.name) / 'env'
        with mock.patch.dict(os.environ, {'GITHUB_ENV': str(env)}):
            result = compat.apply(self.sus, self.ksu, self.common)
        self.assertIn('bridge not applied', result)
        self.assertEqual(before, {p: b for p, b in self.snapshot().items() if p != env})
        self.assertEqual(env.read_text(), 'SELINUX_BACKEND=' + compat.NATIVE_LABEL + '\n')

    def test_extern_declarations_alone_are_not_native(self):
        p = self.ksu / 'selinux/sepolicy.c'
        p.write_text(SEPOLICY.split('static void a')[0])
        self.assertFalse(compat.is_native(self.ksu))
        with self.assertRaisesRegex(ValueError, 'unreviewed BakaSU SELinux contract'):
            compat.validate(self.sus, self.ksu)

    def test_old_single_file_layout_is_never_native(self):
        (self.ksu / 'feature/selinux_hide.c').write_text('// old layout\n')
        self.assertFalse(compat.is_native(self.ksu))

    def test_susfs_without_ledger_rejected(self):
        (self.sus / 'fs/susfs.c').write_text('int other(void)\n{\n}\n')
        with self.assertRaisesRegex(ValueError, 'no ledger function'):
            compat.validate(self.sus, self.ksu)

    def test_native_rejects_bridge_routes_in_kernel(self):
        (self.common / 'security/selinux/selinuxfs.c').write_text(
            'return my_write_access(file, buf, size);\nextern bool ksu_selinux_hide_running;\n')
        with self.assertRaisesRegex(ValueError, 'snapshot bridge routes'):
            compat.apply(self.sus, self.ksu, self.common)

    def test_missing_susfs_selection_rejected(self):
        (self.ksu / 'feature/selinux_hide/selinux_hide.c').write_text('#include "selinux_hide_auto.c"\n')
        with self.assertRaisesRegex(ValueError, 'selection missing'):
            compat.validate(self.sus, self.ksu)


class PriorityIoctlFormTests(unittest.TestCase):
    def test_bare_and_brace_forms_are_recognised(self):
        bare = '    case CMD_SUSFS_SET_PRIORITY_UID_FILTER:\n        susfs_set_priority_uid_filter(arg);\n        return 0;'
        brace = ('    case CMD_SUSFS_SET_PRIORITY_UID_FILTER: {\n        susfs_set_priority_uid_filter(arg);\n'
                 '        return 0;\n    }')
        self.assertEqual(susfs_feature_compat.CALL.search(bare).group(0), bare)
        self.assertEqual(susfs_feature_compat.CALL.search(brace).group(0), brace)

    def test_unbalanced_brace_form_is_rejected(self):
        broken = '    case CMD_SUSFS_SET_PRIORITY_UID_FILTER: {\n        susfs_set_priority_uid_filter(arg);\n        return 0;\n'
        self.assertIsNone(susfs_feature_compat.CALL.search(broken))


class WorkflowTests(unittest.TestCase):
    def test_workflow_no_longer_hardcodes_bridge_label(self):
        wf = (ROOT / '.github/workflows/Build Kernel OnePlus.yml').read_text()
        self.assertNotIn('echo "SELINUX_BACKEND=bakasu-snapshot-bridge-v1"', wf)
        self.assertIn("'SELINUX_BACKEND'", wf)


if __name__ == '__main__':
    unittest.main()
