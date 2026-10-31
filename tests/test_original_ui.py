"""The dispatch UI is byte-for-byte original while latest dependency pins remain."""
import json
from pathlib import Path
import re
import unittest
from test_bakasu_pin import ROOT, WF, step_script

class OriginalUiTests(unittest.TestCase):
    def test_original_input_names_order_types_choices_and_defaults(self):
        ui=WF.read_text().split('on:\n',1)[1].split('\n# 本仓库',1)[0]
        self.assertEqual(ui,(ROOT/'tests/fixtures/original-dispatch-inputs.txt').read_text())

    def test_no_profile_override_layer(self):
        self.assertNotIn('PROFILE',WF.read_text())
        self.assertFalse((ROOT/'scripts/build_profile.py').exists())
        self.assertFalse((ROOT/'scripts/select_susfs.sh').exists())

    def test_latest_inventory_matches_actual_workflow_pins(self):
        versions=json.loads((ROOT/'config/versions.json').read_text())
        text=WF.read_text()
        names={'bakasu':'RESUKISU_COMMIT','sukisu':'SUKISU_BUILTIN_COMMIT','susfs':'BAKASU_SUSFS_COMMIT',
               'kpm':'SUKISU_PATCH_COMMIT','anykernel3':'AK3_COMMIT','bbg':'BBG_COMMIT','sukisu_manager':'MANAGER_SHA'}
        for component,name in names.items():
            pattern=name+r'(?:="|: )([0-9a-f]{40})'
            self.assertEqual(re.search(pattern,text).group(1),versions[component]['commit'],component)
        self.assertIn(versions['kpm']['patch_linux_sha256'],text)

    def test_original_kpm_and_kpn_paths_exist(self):
        text=step_script('Apply KPX and Replace Image')
        self.assertIn('./patch_linux',text)
        self.assertIn('./kptools-linux -p',text)
        self.assertIn('sha256sum --check',text)
        self.assertIn('[[ -s oImage ]]',text)
        for name in ('kpimg-linux','kptools-linux'):
            self.assertTrue((ROOT/'patches'/name).exists())

    def test_default_sukisu_manager_uses_pinned_path_only(self):
        text=WF.read_text().split('      - name: Pair pinned SukiSU Manager\n')[1].split('        run:',1)[0]
        self.assertIn("env.KSU_PINNED == 'true'",text)
        self.assertIn("steps.manager.outputs.manager_artifact == 'Manager'",text)

    def test_failed_manual_susfs_does_not_continue(self):
        text=step_script('Apply SUSFS')
        self.assertIn('::error title=SUSFS::手动指定的 SUSFS',text)
        self.assertNotIn('继续编译，链接阶段可能失败',text)

    def test_free_form_inputs_passed_as_environment_data(self):
        text=WF.read_text()
        for key in ('KSU_META','SUSFS_META','BUILD_TIME','SUFFIX','SUBLEVEL'):
            self.assertIn('INPUT_'+key+': ${{ github.event.inputs.'+key+' }}',text)
        self.assertIn('s = os.environ["INPUT_BUILD_TIME"]',text)

if __name__=='__main__':unittest.main()
