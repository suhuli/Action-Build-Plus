"""Offline checks for the SUSFS pin and existing override behavior.

Run: python3 -m unittest discover -s tests -v
No network access, APK download, or kernel build is performed.
"""
import os
from pathlib import Path
import re
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/Build Kernel OnePlus.yml'
PIN = '31eb14add587b0a089dfe1819f92cc94920e141e'
OLD = 'ca7093a1a26f7911987110c34a1352d74cfb1d09'
BAKA = '5b76b884c75f729a220bb317aa4a4fc78f0e0e9c'
SUKI = '05f5cdf082d32bbc651c205ba4bdd1dc66cca7f5'


class SusfsPinTests(unittest.TestCase):
    def select_source(self, meta='', dev=False):
        """Run the real mode-selection block (stops before git clone). Returns (auto, meta)."""
        source = WF.read_text()
        start = source.index('            STABLE_SUSFS_COMMIT=')
        end = source.index('            git clone https://gitlab.com/simonpunk/susfs4ksu.git', start)
        script = textwrap.dedent(source[start:end])
        script = script.replace('${{ github.event.inputs.SUSFS_DEV }}', 'true' if dev else 'false')
        script += '\nprintf "__SUSFS_SELECTED__=%s|%s" "$SUSFS_AUTO" "$SUSFS_META"\n'
        result = subprocess.run(
            ['bash', '-euo', 'pipefail', '-c', script],
            env={**os.environ, 'SUSFS_META': meta},
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        auto, selected = result.stdout.rsplit('__SUSFS_SELECTED__=', 1)[1].split('|', 1)
        return auto == 'true', selected

    def test_pin_and_documentation_agree(self):
        source = WF.read_text()
        pins = re.findall(r'STABLE_SUSFS_COMMIT="([0-9a-f]{40})"', source)
        self.assertEqual(pins, [PIN])
        for filename in ('README.md', 'README-en.md'):
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text()
                self.assertIn('/-/commit/' + PIN, text)
                self.assertIn('v2.3.0', text)
                self.assertIn(OLD, text)  # Explicit rollback remains documented.

    def test_default_follows_latest_compatible(self):
        self.assertEqual(self.select_source(), (True, ''))

    def test_manual_source_overrides_remain_supported(self):
        for meta in (OLD, '2'):
            with self.subTest(meta=meta):
                self.assertEqual(self.select_source(meta=meta), (False, meta))

    def test_dev_branch_does_not_use_auto_selection(self):
        self.assertEqual(self.select_source(dev=True), (False, ''))

    def test_explicit_dev_commit_is_preserved(self):
        self.assertEqual(self.select_source(meta=OLD, dev=True), (False, OLD))

    def test_kernel_su_pins_are_unchanged(self):
        source = WF.read_text()
        self.assertIn('RESUKISU_COMMIT="' + BAKA + '"', source)
        self.assertIn('SUKISU_BUILTIN_COMMIT="' + SUKI + '"', source)
        self.assertIn(r'Please wait susfs update\.', source)

    def test_apply_step_keeps_existing_branch_and_kernel_patch(self):
        source = WF.read_text()
        block = source.split('      - name: Apply SUSFS\n', 1)[1]
        block = block.split('\n      - name:', 1)[0]
        self.assertIn('https://gitlab.com/simonpunk/susfs4ksu.git', block)
        self.assertIn('gki-${{ env.KANDROID_VERSION }}-${{ env.KERNEL_VERSION }}', block)
        self.assertIn('50_add_susfs_in_gki-${GKI_V}.patch', block)
        self.assertNotIn('10_enable_susfs_for_ksu.patch', block)
        self.assertIn('if [ "${{ github.event.inputs.SUSFS_META }}" != "-1" ]; then', block)
        self.assertIn('susfs_fixups.py" pre .', block)
        self.assertIn('susfs_fixups.py" post .', block)
        self.assertIn('scripts/susfs_ksu_check.py', block)
        self.assertIn('SUSFS_NOTE', block)


if __name__ == '__main__':
    unittest.main()
