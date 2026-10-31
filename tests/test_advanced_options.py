"""Advanced overrides are opt-in and never weaken reviewed preset defaults."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_build_profiles import build_profile, ROOT, VERSIONS


class AdvancedTests(unittest.TestCase):
    def resolve(self, profile='BAKASU', **options):
        return build_profile.resolve(profile, options=options)

    def test_legacy_kernel_hash_overrides_latest_pin(self):
        sha='239e1e8871b8fcd51a6e5b3002e0ba522fdd99fb'
        env=self.resolve(KSU_META='//'+sha)
        self.assertEqual(env['KSU_REF'],sha)
        self.assertEqual(env['KSU_PINNED'],'false')
        self.assertEqual(env['SUSFS_SELECTION'],'compatible')

    def test_branch_label_and_hash_priority(self):
        env=self.resolve(KSU_META='main/test/abcdef123')
        self.assertEqual(env['KSU_REF'],'abcdef123')
        self.assertEqual(env['CUSTOM_TAG'],'test')
        self.assertEqual(self.resolve(KSU_META='main//')['KSU_REF'],'origin/main')

    def test_invalid_meta_rejected(self):
        for value in ('main','///','main/x/not-hex','main/x;bad/','main/x/123','-bad//'):
            with self.subTest(value=value),self.assertRaises(ValueError): self.resolve(KSU_META=value)

    def test_susfs_can_only_be_disabled_for_bakasu(self):
        self.assertEqual(self.resolve(SUSFS_META='-1')['SUSFS_ENABLED'],'false')
        for profile in ('SUKISU','SUKISU_KPM'):
            with self.assertRaises(ValueError):self.resolve(profile,SUSFS_META='-1')

    def test_manual_susfs_commit_count_and_ref(self):
        for value in ('2','HEAD~2','31eb14add587b0a089dfe1819f92cc94920e141e','origin/test'):
            self.assertEqual(self.resolve(SUSFS_META=value)['SUSFS_SELECTION'],'manual')

    def test_dev_and_custom_branch_are_explicit(self):
        env=self.resolve(SUSFS_DEV='true')
        self.assertEqual(env['SUSFS_BRANCH'],'gki-android12-5.10-dev')
        self.assertEqual(env['SUSFS_SELECTION'],'branch')
        self.assertEqual(self.resolve(SUSFS_BRANCH='test')['SUSFS_BRANCH'],'test')

    def test_both_spoof_managers(self):
        baka=self.resolve(MANAGER_SOURCE='RESUKISU_SPOOF')
        self.assertEqual(baka['MANAGER_ARTIFACT'],'Spoofed-Manager-release')
        suki=self.resolve(MANAGER_SOURCE='SUKISU_SPOOF')
        self.assertEqual(suki['MANAGER_ARTIFACT'],'Manager-spoofed')
        self.assertEqual(suki['MANAGER_SPOOF'],'true')

    def test_kpn_only_for_sukisu_and_not_kernel_kpm(self):
        env=self.resolve('SUKISU',KPM='KPN')
        self.assertEqual(env['KPN_ENABLED'],'true')
        self.assertEqual(env['KPM_ENABLED'],'false')
        with self.assertRaises(ValueError):self.resolve(KPM='KPN')

    def test_module_override_can_disable_preset_kpm(self):
        env=self.resolve('SUKISU_KPM',KPM='N/A')
        self.assertEqual(env['KPM_ENABLED'],'false')
        self.assertEqual(env['BUILD_PROFILE'],'SUKISU')

    def test_inputs_cannot_inject_environment_or_shell(self):
        for key,value in [('SUSFS_META','x\nEVIL=true'),('SUSFS_META','$(id)'),('SUSFS_BRANCH','--help'),('SUSFS_BRANCH','a/../b'),('KSU_META','main/$(id)/')]:
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(**{key:value})

    def test_restored_kpn_binary_hashes_match(self):
        legacy=json.loads((ROOT/'config/legacy.json').read_text())
        for name,sha in legacy['kpn_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'patches'/name).read_bytes()).hexdigest(),sha)


class RealSusfsSelectionTests(unittest.TestCase):
    def run_selection(self,mode,meta='',compatible=('old',),floor_missing=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);repo=root/'repo';repo.mkdir();scripts=root/'scripts';scripts.mkdir()
            (scripts/'susfs_ksu_check.py').write_text('import pathlib,sys\nsys.exit(0 if pathlib.Path("name").read_text() in sys.argv[2].split(",") else 1)\n')
            env={**os.environ,'GIT_AUTHOR_NAME':'test','GIT_AUTHOR_EMAIL':'test@example.invalid','GIT_COMMITTER_NAME':'test','GIT_COMMITTER_EMAIL':'test@example.invalid'}
            def git(*args):return subprocess.check_output(['git',*args],cwd=repo,env=env,text=True).strip()
            git('init','-q','-b','main');pins={}
            for name in ('old','new'):
                (repo/'name').write_text(name)
                header=repo/'kernel_patches/include/linux/susfs.h';header.parent.mkdir(parents=True,exist_ok=True);header.write_text('#define SUSFS_VERSION "2.3.0"\n')
                git('add','.');git('commit','-qm',name);pins[name]=git('rev-parse','HEAD')
            target=root/'env';target.touch()
            env.update(GITHUB_WORKSPACE=tmp,GITHUB_ENV=str(target),SUSFS_SELECTION=mode,SUSFS_META=meta,
                       SUSFS_COMMIT=pins['new'],LEGACY_SUSFS_FLOOR='0'*40 if floor_missing else pins['old'],KSU_SRC=','.join(compatible),COMMON_SRC='fixture')
            r=subprocess.run(['bash',str(ROOT/'scripts/select_susfs.sh')],cwd=repo,env=env,text=True,capture_output=True)
            return r,target.read_text(),git('rev-parse','HEAD'),pins

    def test_default_pin_is_used_without_fallback(self):
        r,_,_,_=self.run_selection('pinned',compatible=('old',))
        self.assertNotEqual(r.returncode,0)

    def test_custom_kernel_can_select_compatible_older_susfs(self):
        r,env,selected,pins=self.run_selection('compatible')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(selected,pins['old'])
        self.assertIn('SUSFS_ACTUAL_COMMIT='+selected,env)

    def test_manual_count_selects_old_commit(self):
        r,_,selected,pins=self.run_selection('manual','1')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(selected,pins['old'])

    def test_manual_incompatibility_fails(self):
        r,env,_,_=self.run_selection('manual','0')
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(env,'')

    def test_dev_does_not_implicitly_fall_back(self):
        r,_,_,_=self.run_selection('branch')
        self.assertNotEqual(r.returncode,0)

    def test_missing_floor_only_checks_head(self):
        r,_,_,_=self.run_selection('compatible',floor_missing=True)
        self.assertNotEqual(r.returncode,0)


if __name__=='__main__':unittest.main()
