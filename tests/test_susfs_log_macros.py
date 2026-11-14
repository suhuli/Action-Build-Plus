"""Offline regression for the SUSFS v2.4.0 log-macro fixup (logging disabled build).

Run: python3 -m unittest discover -s tests -v
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/susfs_fixups.py'
HEAD = '''#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
#define SUSFS_LOGI(fmt, ...) pr_info(fmt, ##__VA_ARGS__)
#define SUSFS_LOGE(fmt, ...) pr_err(fmt, ##__VA_ARGS__)
%s#else
#define SUSFS_LOGI(fmt, ...) 
#define SUSFS_LOGE(fmt, ...) 
#endif
'''
RL = ('#define SUSFS_LOGI_RL(fmt, ...) pr_info_ratelimited(fmt, ##__VA_ARGS__)\n'
      '#define SUSFS_LOGE_RL(fmt, ...) pr_err_ratelimited(fmt, ##__VA_ARGS__)\n')
BODY = 'int f(void) {\n\tSUSFS_LOGI("a");\n\tSUSFS_LOGI_RL("b");\n\treturn 0;\n}\n'


class LogMacroFixupTests(unittest.TestCase):
    def run_post(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'fs/susfs.c'
            target.parent.mkdir()
            target.write_text(text)
            result = subprocess.run([sys.executable, str(SCRIPT), 'post', tmp],
                                    text=True, capture_output=True)
            return result, target.read_text()

    def test_adds_only_used_missing_macro(self):
        result, out = self.run_post(HEAD % RL + BODY)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('#ifndef SUSFS_LOGI_RL\n#define SUSFS_LOGI_RL(fmt, ...)\n#endif\n', out)
        self.assertNotIn('#ifndef SUSFS_LOGE_RL', out)  # defined upstream but unused
        self.assertTrue(out.endswith(BODY))

    def test_idempotent(self):
        _, once = self.run_post(HEAD % RL + BODY)
        result, twice = self.run_post(once)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(once, twice)

    def test_old_susfs_is_untouched(self):
        text = HEAD % '' + 'int f(void) {\n\tSUSFS_LOGI("a");\n\treturn 0;\n}\n'
        result, out = self.run_post(text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(out, text)

    def test_macro_undefined_everywhere_fails(self):
        result, out = self.run_post(HEAD % '' + BODY)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(out, HEAD % '' + BODY)


if __name__ == '__main__':
    unittest.main()
