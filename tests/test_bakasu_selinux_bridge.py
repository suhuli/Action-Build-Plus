"""Real-source patch regressions. Not a substitute for a kernel/device test."""
import gzip
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bakasu_selinux_compat import apply, validate, verify


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        fixture = ROOT / 'tests/fixtures/bakasu_selinux'
        for p in fixture.rglob('*.gz'):
            dest = self.root / str(p.relative_to(fixture))[:-3]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(gzip.decompress(p.read_bytes()))
        self.sus = self.root / 'susfs'
        self.ksu = self.root / 'ksu'

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_check_does_not_mutate_sources(self):
        before = self.snapshot()
        validate(self.sus, self.ksu)
        self.assertEqual(before, self.snapshot())

    def test_real_oem_patch_applies_and_is_idempotent(self):
        self.assertEqual(apply(self.sus, self.ksu, self.root), 'applied')
        before = self.snapshot()
        self.assertEqual(apply(self.sus, self.ksu, self.root), 'already applied')
        self.assertEqual(before, self.snapshot())
        verify(self.root)

    def test_unreviewed_bakasu_is_rejected(self):
        p = self.ksu / 'feature/selinux_hide.c'
        p.write_text(p.read_text() + '\n/* upstream change */\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'unreviewed BakaSU'):
            apply(self.sus, self.ksu, self.root)
        self.assertEqual(before, self.snapshot())

    def test_unreviewed_susfs_is_rejected(self):
        p = next(self.sus.glob('*.patch'))
        p.write_text(p.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'unreviewed SUSFS'):
            validate(self.sus, self.ksu)

    def test_unknown_kernel_hook_layout_fails_without_mutation(self):
        p = self.root / 'security/selinux/selinuxfs.c'
        p.write_text(p.read_text().replace('return susfs_sel_write_access(file, buf, size);', 'return -1;'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'dry-run failed'):
            apply(self.sus, self.ksu, self.root)
        self.assertEqual(before, self.snapshot())

    def test_all_three_routes_and_eligibility_guards(self):
        paths = [self.root / 'security/selinux' / p for p in ['hooks.c', 'selinuxfs.c']]
        before = [p.read_text() for p in paths]
        apply(self.sus, self.ksu, self.root)
        for p, original in zip(paths, before):
            updated = p.read_text()
            for guard in ['current_uid().val >= 10000', 'ksu_selinux_hide_running']:
                self.assertEqual(original.count(guard), updated.count(guard))
        hooks, fs = [p.read_text() for p in paths]
        self.assertIn('!strcmp(name, "current")', hooks)
        self.assertIn('return selinux_setprocattr(name, value, size);', hooks)
        self.assertIn('return sel_write_context(file, buf, size);', fs)
        self.assertIn('return sel_write_access(file, buf, size);', fs)
        self.assertNotIn('static int susfs_selinux_setprocattr(', hooks)
        self.assertNotIn('static ssize_t susfs_sel_write_context(', fs)
        self.assertNotIn('static ssize_t susfs_sel_write_access(', fs)

    def test_backend_security_checks_and_lifecycle_not_modified(self):
        before = {p: p.read_bytes() for p in self.ksu.rglob('*') if p.is_file()}
        apply(self.sus, self.ksu, self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in self.ksu.rglob('*') if p.is_file()})
        text = (self.ksu / 'feature/selinux_hide.c').read_text()
        for check in ['SECURITY__CHECK_CONTEXT', 'SECURITY__COMPUTE_AV', 'PROCESS__SETCURRENT',
                      'backup_sepolicy', 'return -EAGAIN;']:
            self.assertIn(check, text)

    def test_workflow_checks_and_applies_bakasu_only(self):
        wf = (ROOT / '.github/workflows/Build Kernel OnePlus.yml').read_text()
        self.assertIn('if [[ "$IS_RESUKISU" == true ]]; then\n                python3 "$GITHUB_WORKSPACE/scripts/bakasu_selinux_compat.py" --check', wf)
        self.assertIn('if [[ "$IS_RESUKISU" == true ]]; then\n              python3 "$GITHUB_WORKSPACE/scripts/bakasu_selinux_compat.py" --apply', wf)
        self.assertIn('SUSFS_META="$BAKASU_SUSFS_COMMIT"', wf)
        self.assertLess(wf.index('bakasu_selinux_compat.py" --apply'), wf.index('- name: Apply UNICODE_BYPASS'))


if __name__ == '__main__':
    unittest.main()
