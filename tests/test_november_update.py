"""Synthetic regressions; no kernel build or device-safety claims."""
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import importlib.util
from test_susfs_auto import make_susfs, write, run_check
from test_bakasu_pin import ROOT, WF, step_script
sys.path.insert(0,str(ROOT/'scripts'))
from susfs_feature_compat import plan, FLAG
from manager_variant_check import check

STANZA='''+config KSU_SUSFS_PRIORITY_UID_FILTER
+\tbool "priority uid filter"
+\tdepends on KSU_SUSFS
+\tdefault y
+\n+endmenu
'''
BLOCK='''        case CMD_SUSFS_SET_PRIORITY_UID_FILTER:
            susfs_set_priority_uid_filter(arg);
            return 0;'''

class FeatureContractTests(unittest.TestCase):
    def fixture(self,root,guard=True,caller=True):
        sus=root/'sus';ksu=root/'ksu'
        write(sus/'fs/susfs.c',('#ifdef '+FLAG+'\n' if guard else '')+'void susfs_set_priority_uid_filter(void *arg) {}\n'+('#endif\n' if guard else ''))
        write(sus/'include/linux/susfs.h',('#ifdef '+FLAG+'\n' if guard else '')+'void susfs_set_priority_uid_filter(void *arg);\n'+('#endif\n' if guard else ''))
        write(sus/'KernelSU/10_enable_susfs_for_ksu.patch',STANZA)
        write(ksu/'Kconfig','menu "SUSFS"\nconfig KSU_SUSFS_SUS_MAP\n\tbool "map"\nendmenu\n')
        write(ksu/'supercall/dispatch.c','void handle(void) {\nswitch(0) {\n'+(BLOCK if caller else '')+'\n}\n}\n')
        write(ksu/'manager/pkg_observer.c','void observe(void) {\n    susfs_parse_priority_app_strings();\n}\n')
        return sus,ksu

    def test_check_is_nonmutating(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp));before={p:p.read_bytes() for p in ksu.rglob('*') if p.is_file()}
            changes=plan(sus,ksu);self.assertEqual(len(changes),3)
            self.assertEqual(before,{p:p.read_bytes() for p in ksu.rglob('*') if p.is_file()})

    def test_apply_is_idempotent_and_uses_upstream_stanza(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp))
            for p,s in plan(sus,ksu).items():p.write_text(s)
            self.assertEqual(plan(sus,ksu),{})
            self.assertIn('default y',(ksu/'Kconfig').read_text())
            for name in ['supercall/dispatch.c','manager/pkg_observer.c']:
                self.assertIn('#ifdef '+FLAG,(ksu/name).read_text())

    def test_legacy_susfs_does_not_get_new_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp),guard=False);self.assertEqual(plan(sus,ksu),{})

    def test_bakasu_without_real_uid_integration_does_not_gain_fake_feature(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp),caller=False);self.assertEqual(plan(sus,ksu),{})

    def test_missing_upstream_stanza_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp));(sus/'KernelSU/10_enable_susfs_for_ksu.patch').write_text('')
            with self.assertRaises(ValueError):plan(sus,ksu)

    def test_unknown_dispatch_layout_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp));p=ksu/'supercall/dispatch.c';p.write_text(p.read_text().replace('return 0;','return -1;'))
            with self.assertRaises(ValueError):plan(sus,ksu)

    def test_invalid_existing_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp));p=ksu/'Kconfig'
            p.write_text(p.read_text()+'config KSU_SUSFS_PRIORITY_UID_FILTER\n\tstring "wrong"\n')
            with self.assertRaises(ValueError):plan(sus,ksu)

    def test_extra_unreviewed_caller_in_same_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp));p=ksu/'supercall/dispatch.c'
            p.write_text(p.read_text()+'void extra(void) {susfs_set_priority_uid_filter(arg);}')
            with self.assertRaises(ValueError):plan(sus,ksu)

    def test_selected_av_rule_width_is_aligned(self):
        with tempfile.TemporaryDirectory() as tmp:
            sus,ksu=self.fixture(Path(tmp))
            p=sus/'fs/susfs.c';p.write_text(p.read_text()+'int susfs_add_sus_avd_allowed_by_type(u32 s_type, u32 t_type, u32 c_type, u32 orig_avd_allowed) {}\n')
            write(ksu/'selinux/sepolicy.c','extern int susfs_add_sus_avd_allowed_by_type(u32 s_type, u32 t_type, u16 type, u32 orig_avd_allowed);\n')
            self.assertIn('u32 type',plan(sus,ksu)[ksu/'selinux/sepolicy.c'])

class ReverseContractTests(unittest.TestCase):
    def test_new_kernel_rejects_old_susfs_without_real_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sus=make_susfs(root/'s','extern int ksu_hook(void);')
            write(root/'ksu/code.c','int ksu_hook(void) {}\nvoid use(void) {\n susfs_add_sus_type("domain", 1);\n}\n')
            r=run_check(sus,root/'ksu');self.assertEqual(r.returncode,1);self.assertIn('susfs_add_sus_type',r.stdout)

    def test_real_external_definition_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sus=make_susfs(root/'s','extern int ksu_hook(void);','int susfs_add_sus_type(const char *name, int id) {}\n')
            write(root/'ksu/code.c','int ksu_hook(void) {}\nvoid use(void) {\n susfs_add_sus_type("domain", 1);\n}\n')
            self.assertEqual(run_check(sus,root/'ksu').returncode,0)

    def test_static_c_implementation_is_not_an_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sus=make_susfs(root/'s','extern int ksu_hook(void);','static int susfs_add_sus_type(const char *name, int id) {}\n')
            write(root/'ksu/code.c','int ksu_hook(void) {}\nvoid use(void) {\n susfs_add_sus_type("domain", 1);\n}\n')
            self.assertEqual(run_check(sus,root/'ksu').returncode,1)

    def test_other_ksu_file_static_definition_cannot_satisfy_external_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sus=make_susfs(root/'s','extern int ksu_hook(void);')
            write(root/'ksu/one.c','int ksu_hook(void) {}\nstatic void susfs_missing(void) {}\n')
            write(root/'ksu/two.c','void use(void) {\n susfs_missing();\n}\n')
            self.assertEqual(run_check(sus,root/'ksu').returncode,1)

class VariantTests(unittest.TestCase):
    def test_removed_spoof_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'workflow';p.write_text('name: Manager-release\n');self.assertFalse(check(p))

    def test_legacy_spoof_source_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'workflow';p.write_text('Spoofed-Manager-release\nKSU_PACKAGE_NAME\nmanager_type: spoofed\n');self.assertTrue(check(p))

    def test_variant_check_runs_before_compilation_and_no_silent_substitution(self):
        self.assertIn('manager_variant_check.py',step_script('Add KernelSU'))
        self.assertNotIn('改为附带同版本的普通管理器',step_script('Download Manager APK'))

    def test_effective_feature_config_is_checked(self):
        self.assertIn('CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y',WF.read_text())
        self.assertIn('not enabled in the effective config',WF.read_text())
        self.assertIn('susfs_feature_compat.py" --check',step_script('Apply SUSFS'))
        self.assertIn('susfs_feature_compat.py" --apply',step_script('Apply SUSFS'))

if __name__=='__main__':unittest.main()
