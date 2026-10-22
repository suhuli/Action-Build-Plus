"""Offline tests for SUSFS auto-selection and the SUSFS ↔ KernelSU interface check.

Run: python3 -m unittest discover -s tests -v
Uses small synthetic sources and a local git repo; no network or kernel build.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/Build Kernel OnePlus.yml'
CHECK = ROOT / 'scripts/susfs_ksu_check.py'

PATCH_HEAD = 'diff --git a/fs/exec.c b/fs/exec.c\n--- a/fs/exec.c\n+++ b/fs/exec.c\n@@ -1,3 +1,9 @@\n'


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))


def make_susfs(root: Path, externs: str, susfs_c: str = '') -> Path:
    kp = root / 'kernel_patches'
    body = ''.join('+' + l + '\n' for l in textwrap.dedent(externs).strip().splitlines())
    write(kp / '50_add_susfs_in_gki-android12-5.10.patch', PATCH_HEAD + body)
    write(kp / 'fs/susfs.c', susfs_c)
    write(kp / 'include/linux/susfs.h', '')
    return kp


def run_check(kp: Path, ksu: Path, common: Path = None):
    args = ['python3', str(CHECK), str(kp), str(ksu)] + ([str(common)] if common else [])
    return subprocess.run(args, text=True, capture_output=True)


class InterfaceCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_symbols_exported(self):
        kp = make_susfs(self.root / 's', '''
            #ifdef CONFIG_KSU_SUSFS
            extern int ksu_handle_stat(int *dfd, struct filename **filename,
                                       int *flags);
            extern __attribute__((cold)) void ksu_handle_sys_read(unsigned int fd);
            extern bool ksu_selinux_hide_running __read_mostly;
            extern struct static_key_true ksu_is_input_hook_enabled;
            extern bool susfs_is_inode_sus_path(struct inode *inode);
            #endif
        ''', susfs_c='__attribute__((hot)) bool susfs_is_inode_sus_path(struct inode *inode) {\n}\n')
        write(self.root / 'ksu/a.c', '''
            int ksu_handle_stat(int *dfd, struct filename **filename,
                                int *flags)
            {
                return 0;
            }
            __attribute__((cold)) void ksu_handle_sys_read(unsigned int fd) {}
            // remove static in susfs
            __maybe_static bool ksu_selinux_hide_running __read_mostly = false;
            #ifdef CONFIG_KSU_SUSFS
                DEFINE_STATIC_KEY_TRUE(ksu_is_input_hook_enabled);
            #endif
        ''')
        r = run_check(kp, self.root / 'ksu')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('检查通过', r.stdout)

    def test_static_or_missing_symbols_fail(self):
        kp = make_susfs(self.root / 's', '''
            extern ssize_t my_write_context(struct file *file, char *buf, size_t size);
            extern int my_setprocattr(const char *name, void *value, size_t size);
        ''')
        write(self.root / 'ksu/selinux_hide.c', '''
            static ssize_t my_write_context(struct file *file, char *buf, size_t size)
            {
                return 0;
            }
            static void use(void) { setprocattr_fn my_setprocattr = other; }
        ''')
        r = run_check(kp, self.root / 'ksu')
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertRegex(r.stdout, r'my_write_context: KernelSU 中只有 static 定义')
        self.assertRegex(r.stdout, r'my_setprocattr: KernelSU 中没有定义')

    def test_kernel_provided_symbol_is_accepted(self):
        kp = make_susfs(self.root / 's', 'extern struct selinux_state selinux_state;')
        write(self.root / 'ksu/a.c', '')
        write(self.root / 'common/security/selinux/hooks.c', 'struct selinux_state selinux_state;\n')
        self.assertEqual(run_check(kp, self.root / 'ksu').returncode, 1)
        r = run_check(kp, self.root / 'ksu', self.root / 'common')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_multiline_prototype_is_not_a_function_definition(self):
        kp = make_susfs(self.root / 's', 'extern int missing_handler(int value);')
        write(self.root / 'ksu/a.c', '''
            int missing_handler(int value,
                                int other);
        ''')
        r = run_check(kp, self.root / 'ksu')
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('missing_handler', r.stdout)

    def test_conditional_signature_with_shared_body_is_a_definition(self):
        kp = make_susfs(self.root / 's', 'extern bool helper(struct inode *inode);', susfs_c='''
            #if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 6, 0)
            bool helper(struct mnt_idmap *idmap, struct inode *inode)
            #else
            bool helper(struct inode *inode)
            #endif
            {
                return true;
            }
        ''')
        write(self.root / 'ksu/a.c', '')
        r = run_check(kp, self.root / 'ksu')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_bad_arguments(self):
        self.assertEqual(run_check(self.root / 'nope', self.root / 'nope').returncode, 2)


def selection_script():
    source = WF.read_text()
    block = source.split('      - name: Apply SUSFS\n', 1)[1].split('\n      - name:', 1)[0]
    a = block.index('            # --- 选择 SUSFS 提交 ---')
    b = block.index('            # --- 选择结束 ---')
    return textwrap.dedent(block[a:b])


class AutoSelectTests(unittest.TestCase):
    """Run the real selection block against a local git repo with a stubbed checker."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t',
               'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}
        self.env = env
        git = lambda *a: subprocess.run(['git', *a], cwd=self.repo, env=env, check=True,
                                        capture_output=True, text=True).stdout.strip()
        git('init', '-q', '-b', 'main')
        self.commits = {}
        for name in ('old', 'stable', 'new1', 'new2', 'head'):
            (self.repo / 'name').write_text(name)
            git('add', '-A')
            git('commit', '-q', '-m', name)
            self.commits[name] = git('rev-parse', 'HEAD')

    def tearDown(self):
        self.tmp.cleanup()

    def pick(self, compatible, stable='stable'):
        # Stub checker: compatible iff the commit name is in the set
        names = {sha: n for n, sha in self.commits.items()}
        ok = ' '.join(self.commits[n] for n in compatible)
        script = ('susfs_ok() { [[ " $OK " == *" $(git rev-parse HEAD) "* ]]; }\n'
                  'SUSFS_AUTO=true; SUSFS_NOTE=""\n'
                  f'STABLE_SUSFS_COMMIT={stable if len(stable) == 40 else self.commits[stable]}\n'
                  + selection_script() +
                  '\nprintf "__PICK__=%s|%s" "$(git rev-parse HEAD)" "$SUSFS_NOTE"\n')
        subprocess.run(['git', 'checkout', '-q', 'main'], cwd=self.repo, check=True)
        r = subprocess.run(['bash', '-eo', 'pipefail', '-c', script], cwd=self.repo,
                           env={**self.env, 'OK': ok}, text=True, capture_output=True)
        if r.returncode:
            return None, r.stdout + r.stderr
        sha, note = r.stdout.rsplit('__PICK__=', 1)[1].split('|', 1)
        return names[sha], note

    def test_uses_head_when_compatible(self):
        self.assertEqual(self.pick({'stable', 'head'}), ('head', ''))

    def test_walks_back_to_newest_compatible(self):
        name, note = self.pick({'stable', 'new1'})
        self.assertEqual(name, 'new1')
        self.assertIn('已自动使用', note)

    def test_falls_back_to_stable(self):
        name, note = self.pick({'old', 'stable'})
        self.assertEqual(name, 'stable')
        self.assertIn(self.commits['head'][:8], note)

    def test_never_goes_older_than_stable(self):
        name, out = self.pick({'old'})
        self.assertIsNone(name)
        self.assertIn('没有找到与当前 KernelSU 接口兼容的 SUSFS 提交', out)

    def test_missing_stable_only_checks_head(self):
        name, out = self.pick({'old', 'stable'}, stable='0' * 40)
        self.assertIsNone(name)
        self.assertIn('已不在分支历史中', out)
        self.assertEqual(self.pick({'head'}, stable='0' * 40), ('head', ''))


if __name__ == '__main__':
    unittest.main()
