"""Offline downstream-profile regression tests. No network or complete kernel build."""
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from bakasu_susfs_compat import (CompatError, HEADER, INCLUDE, PREINIT_SYMBOLS,
                                 guarded_preinit_lines, install, load_profile,
                                 without_preinit_blocks)
from bakasu_manager_pair import PairingError, inspect
from build_provenance import provenance
from test_bakasu_pin import bash, step_script

WF = ROOT / ".github/workflows/Build Kernel OnePlus.yml"
PROFILE = """/* Test fixture: versioned explicit legacy-init profile. */
#ifndef __BAKASU_SUSFS_COMPAT_H
#define __BAKASU_SUSFS_COMPAT_H
#define BAKASU_SUSFS_COMPAT_VERSION 1
#ifdef CONFIG_KSU_SUSFS
#define KSU_NO_PREINIT 1
#endif
#endif
"""
EXEC = """#ifdef CONFIG_KSU_SUSFS
#include <linux/susfs_def.h>
#ifndef KSU_NO_PREINIT
extern int ksu_setup_preinit_file(void);
extern int ksu_preinit_handle_post_execveat(void);
#endif
#endif
void exec_fixture(void)
{
#ifdef CONFIG_KSU_SUSFS
#ifndef KSU_NO_PREINIT
    ksu_setup_preinit_file();
    ksu_preinit_handle_post_execveat();
#endif
#endif
}
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.ksu, self.common = root / "kernel", root / "common"
        write(self.ksu / "include" / HEADER, PROFILE)
        write(self.ksu / "runtime/ksud_integration.c",
              'static const char KERNEL_SU_RC[] = KSUD_PATH;\n'
              'DEFINE_STATIC_KEY_TRUE(ksu_is_init_rc_hook_enabled);\n')
        write(self.common / "Makefile", "VERSION = 5\nPATCHLEVEL = 10\nSUBLEVEL = 110\n")
        write(self.common / "fs/exec.c", EXEC)
        write(self.common / "security/selinux/hooks.c", "bool ksu_selinux_hide_running; int my_setprocattr(void);\n")
        write(self.common / "security/selinux/selinuxfs.c", "int my_write_context(void); int my_write_access(void);\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_is_explicit_and_idempotent(self):
        self.assertTrue(install(self.ksu, self.common))
        source = (self.common / "fs/exec.c").read_text()
        self.assertEqual(source.count(INCLUDE), 1)
        self.assertLess(source.index(INCLUDE), source.index(PREINIT_SYMBOLS[0]))
        self.assertEqual((self.common / "include/linux" / HEADER).read_text(), PROFILE)
        self.assertFalse(install(self.ksu, self.common))
        self.assertFalse(install(self.ksu, self.common, check_only=True))

    def test_check_never_writes(self):
        with self.assertRaisesRegex(CompatError, "not been installed"):
            install(self.ksu, self.common, check_only=True)
        self.assertFalse((self.common / "include/linux" / HEADER).exists())
        self.assertEqual((self.common / "fs/exec.c").read_text(), EXEC)

    def test_unguarded_preinit_call_fails_before_any_write(self):
        path = self.common / "fs/exec.c"
        path.write_text(EXEC + "int x() { return ksu_setup_preinit_file(); }\n")
        with self.assertRaisesRegex(CompatError, "not protected"):
            install(self.ksu, self.common)
        self.assertFalse((self.common / "include/linux" / HEADER).exists())
        self.assertNotIn(INCLUDE, path.read_text())

    def test_wrong_kernel_series_is_rejected(self):
        (self.common / "Makefile").write_text("VERSION = 6\nPATCHLEVEL = 12\n")
        with self.assertRaisesRegex(CompatError, "only supports Linux 5.10"):
            install(self.ksu, self.common)

    def test_upstream_or_old_fork_cannot_claim_profile(self):
        (self.ksu / "include" / HEADER).unlink()
        with self.assertRaisesRegex(CompatError, "missing versioned"):
            install(self.ksu, self.common)

    def test_unknown_profile_version_is_rejected(self):
        (self.ksu / "include" / HEADER).write_text(PROFILE.replace("VERSION 1", "VERSION 2"))
        with self.assertRaisesRegex(CompatError, "expected 1"):
            load_profile(self.ksu)

    def test_header_without_optout_is_rejected(self):
        (self.ksu / "include" / HEADER).write_text(PROFILE.replace("#define KSU_NO_PREINIT 1", ""))
        with self.assertRaisesRegex(CompatError, "explicitly define"):
            load_profile(self.ksu)

    def test_inactive_header_optout_cannot_claim_profile(self):
        (self.ksu / "include" / HEADER).write_text("#if 0\n" + PROFILE + "#endif\n")
        with self.assertRaisesRegex(CompatError, "contract has changed"):
            load_profile(self.ksu)

    def test_foreign_installed_header_is_rejected(self):
        write(self.common / "include/linux" / HEADER, "#define KSU_NO_PREINIT 1\n")
        with self.assertRaisesRegex(CompatError, "does not match"):
            install(self.ksu, self.common)

    def test_late_include_is_rejected(self):
        (self.common / "fs/exec.c").write_text(EXEC + INCLUDE + "\n")
        with self.assertRaisesRegex(CompatError, "must precede"):
            install(self.ksu, self.common)

    def test_missing_real_legacy_runtime_is_rejected(self):
        (self.ksu / "runtime/ksud_integration.c").write_text("void no_runtime(void) {}\n")
        with self.assertRaisesRegex(CompatError, "runtime has changed"):
            install(self.ksu, self.common)

    def test_unmanaged_optout_is_rejected(self):
        (self.common / "fs/exec.c").write_text("#define KSU_NO_PREINIT 1\n" + EXEC)
        with self.assertRaisesRegex(CompatError, "unmanaged"):
            install(self.ksu, self.common)

    def test_missing_current_selinux_hook_is_rejected(self):
        (self.common / "security/selinux/hooks.c").write_text("/* old hooks */\n")
        with self.assertRaisesRegex(CompatError, "SELinux integration"):
            install(self.ksu, self.common)


class ConditionalTests(unittest.TestCase):
    def test_unknown_config_branches_are_both_kept(self):
        lines = "#ifdef CONFIG_UNKNOWN\nextern int first;\n#else\nextern int second;\n#endif".splitlines()
        result = "\n".join(without_preinit_blocks(lines))
        self.assertIn("first", result)
        self.assertIn("second", result)

    def test_nested_optional_preinit_is_excluded(self):
        lines = ("#ifdef CONFIG_KSU_SUSFS\n#ifndef KSU_NO_PREINIT\n"
                 "#ifdef CONFIG_COMPAT\nextern int ksu_setup_preinit_file(void);\n"
                 "#endif\n#else\nextern int still_required;\n#endif\n#endif").splitlines()
        result = "\n".join(guarded_preinit_lines(lines))
        self.assertNotIn("ksu_setup_preinit_file", result)
        self.assertIn("still_required", result)

    def test_known_elif_and_else(self):
        lines = ("#if !defined(KSU_NO_PREINIT)\nbad\n"
                 "#elif defined(KSU_NO_PREINIT)\ngood\n#else\nbad2\n#endif").splitlines()
        self.assertEqual(without_preinit_blocks(lines), ["good"])

    def test_unguarded_preinit_is_never_allowlisted(self):
        for symbol in PREINIT_SYMBOLS:
            with self.subTest(symbol=symbol):
                with self.assertRaisesRegex(CompatError, "not protected"):
                    guarded_preinit_lines(["extern int " + symbol + "(void);"])

    def test_comments_are_not_references(self):
        self.assertEqual(guarded_preinit_lines(["/* ksu_setup_preinit_file is absent */"]), [])


class ProfileCheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.kp, self.ksu = self.root / "kernel_patches", self.root / "ksu"
        write(self.ksu / "include" / HEADER, PROFILE)
        write(self.ksu / "a.c", "int required(void) { return 0; }\n")
        code = ("extern int required(void);\n#ifndef KSU_NO_PREINIT\n"
                "extern int ksu_setup_preinit_file(void);\n"
                "extern int ksu_preinit_handle_post_execveat(void);\n#endif\n")
        self.patch = self.kp / "50_add_susfs_in_gki-android12-5.10.patch"
        write(self.patch, "diff --git a/fs/exec.c b/fs/exec.c\n" + "".join("+" + line + "\n" for line in code.splitlines()))

    def tearDown(self):
        self.tmp.cleanup()

    def run_checker(self, flag=True):
        command = [sys.executable, str(SCRIPTS / "susfs_ksu_check.py"), str(self.kp), str(self.ksu)]
        if flag:
            command.append("--bakasu-legacy-init")
        return subprocess.run(command, text=True, capture_output=True)

    def test_profile_can_exclude_only_guarded_optional_calls(self):
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NOT a preinit implementation", result.stdout)
        self.assertIn("1 个", result.stdout)

    def test_default_checker_still_requires_both_preinit_interfaces(self):
        result = self.run_checker(flag=False)
        self.assertEqual(result.returncode, 1, result.stdout)
        for symbol in PREINIT_SYMBOLS:
            self.assertIn(symbol, result.stdout)

    def test_profile_flag_cannot_fix_unpatched_upstream(self):
        (self.ksu / "include" / HEADER).unlink()
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("missing versioned", result.stdout)

    def test_other_missing_symbol_still_fails(self):
        with self.patch.open("a") as stream:
            stream.write("+extern int another_missing(void);\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("another_missing", result.stdout)

    def test_unguarded_preinit_call_fails_even_without_extern(self):
        with self.patch.open("a") as stream:
            stream.write("+retval = ksu_setup_preinit_file();\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("not protected", result.stdout)


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
        self.git("init", "-q", "-b", "main")
        for path in ("manager/a", "userspace/a"):
            write(self.root / path, "unchanged upstream source\n")
        write(self.root / "uapi/supercall.h", "enum { KERNEL_SU_UAPI_VERSION = 5 };\n")
        write(self.root / "kernel/Kbuild",
              "KSU_VERSION_REF := $(shell cat $(KSU_SRC)/tools/susfs_manager_commit)\n"
              "KSU_LOCAL_VERSION := $(shell git rev-list --count $(KSU_VERSION_REF))\n")
        self.commit("upstream base")
        self.base = self.git("rev-parse", "HEAD")
        write(self.root / "kernel/include" / HEADER, PROFILE)
        write(self.root / "kernel/tools/susfs_manager_commit", self.base + "\n")
        self.commit("kernel-only repair")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              text=True, capture_output=True).stdout.strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def test_downstream_commit_does_not_inflate_manager_version(self):
        result = inspect(self.root)
        self.assertEqual(result["manager_sha"], self.base)
        self.assertNotEqual(result["kernel_sha"], self.base)
        self.assertEqual(result["manager_version_code"], 30701)
        self.assertEqual(result["uapi_version"], 5)

    def test_modified_manager_or_userspace_or_uapi_cannot_reuse_apk(self):
        for path in ("manager/a", "userspace/a", "uapi/supercall.h"):
            with self.subTest(path=path):
                file = self.root / path
                original = file.read_text()
                file.write_text(original + "changed\n")
                with self.assertRaisesRegex(PairingError, "differ"):
                    inspect(self.root)
                file.write_text(original)

    def test_untracked_userspace_addition_is_not_silently_accepted(self):
        write(self.root / "userspace/new-source.c", "void changed(void) {}\n")
        with self.assertRaisesRegex(PairingError, "differ"):
            inspect(self.root)

    def test_invalid_manager_pin_is_rejected(self):
        (self.root / "kernel/tools/susfs_manager_commit").write_text("main\n")
        with self.assertRaisesRegex(PairingError, "full upstream"):
            inspect(self.root)

    def test_missing_version_binding_is_rejected(self):
        (self.root / "kernel/Kbuild").write_text("KSU_VERSION := 12345\n")
        with self.assertRaisesRegex(PairingError, "does not bind"):
            inspect(self.root)


class WorkflowRoutingTests(unittest.TestCase):
    def route(self, source, susfs=""):
        script = step_script("Resolve Manager Source")
        script = script.replace("${{ github.event.inputs.MANAGER_SOURCE }}", source)
        script = script.replace("${{ github.event.inputs.SUSFS_META }}", susfs)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "outputs"
            output.touch()
            result = bash(script, {"GITHUB_OUTPUT": str(output)})
            values = dict(line.split("=", 1) for line in output.read_text().splitlines())
            return result, values

    def test_new_default_is_repaired_bakasu(self):
        source = WF.read_text()
        self.assertIn("default: BAKASU", source)
        pin = (ROOT / "manifests/bakasu-susfs.commit").read_text().strip()
        self.assertRegex(pin, r"^[0-9a-f]{40}$")

    def test_bakasu_uses_fork_kernel_and_official_manager(self):
        for source in ("BAKASU", "BAKASU_SPOOF"):
            with self.subTest(source=source):
                result, values = self.route(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["kernel_repo"], "suhuli/BakaSU")
                self.assertEqual(values["manager_repo"], "Baka-SU/BakaSU")
                self.assertEqual(values["default_ksu_branch"], "susfs-android12-5.10")
                self.assertEqual(values["bakasu_compat"], "true")

    def test_legacy_bakasu_fallback_is_unchanged(self):
        result, values = self.route("RESUKISU")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["kernel_repo"], "Baka-SU/BakaSU")
        self.assertEqual(values["bakasu_compat"], "false")

    def test_sukisu_remains_separate(self):
        result, values = self.route("SUKISU")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["kernel_repo"], "SukiSU-Ultra/SukiSU-Ultra")
        self.assertEqual(values["default_ksu_branch"], "builtin")
        self.assertEqual(values["bakasu_compat"], "false")

    def test_new_profile_cannot_disable_required_susfs(self):
        for source in ("BAKASU", "SUKISU"):
            with self.subTest(source=source):
                result, _ = self.route(source, "-1")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("不能关闭 SUSFS", result.stdout)

    def test_legacy_bakasu_can_still_disable_susfs(self):
        result, _ = self.route("RESUKISU", "-1")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_repaired_source_has_its_own_default_pin(self):
        source = WF.read_text()
        a = source.index('          EXPECT_COMMIT=""')
        b = source.index('          echo "KernelSU:', a)
        script = textwrap.dedent(source[a:b])
        pin = "d" * 40  # synthetic local fixture, never sent to a remote API
        result = bash(script + '\nprintf "%s|%s" "$KSU_REF" "$EXPECT_COMMIT"', dict(
            USER_BRANCH="", MANUAL_HASH="", IS_BAKASU_COMPAT="true", IS_RESUKISU="true",
            BAKASU_COMPAT_COMMIT=pin, RESUKISU_COMMIT="e" * 40, SUKISU_BUILTIN_COMMIT="f" * 40))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, pin + "|" + pin)

    def test_manager_query_uses_verified_source_sha_not_fork_sha(self):
        source = step_script("Download Manager APK")
        self.assertIn('MANAGER_SHA="${KSU_MANAGER_SHA:-$KSU_SHA}"', source)
        self.assertIn("head_sha=${MANAGER_SHA}", source)
        self.assertIn('.head_sha == \\"$MANAGER_SHA\\"', source)

    def test_bridge_installed_only_for_repaired_mode(self):
        source = step_script("Apply SUSFS")
        self.assertIn('if [[ "${IS_BAKASU_COMPAT:-false}" == true ]]; then\n    python3', source)
        self.assertIn('bakasu_susfs_compat.py" "$KSU_SRC" . --check', source)

    def test_experimental_release_is_always_prerelease(self):
        source = step_script("Publish Release")
        self.assertIn('"${IS_BAKASU_COMPAT:-false}" == "true"', source)
        self.assertIn('PRE="--prerelease"', source)

    def test_version_mismatch_is_fatal_only_in_repaired_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "env"
            output.touch()
            (root / "build.log").write_text("-- BakaSU version code: 35237\n-- BakaSU version name: v4.2.0-patched\n")
            result = bash(step_script("Detect KSU Version"), dict(
                GITHUB_WORKSPACE=tmp, GITHUB_ENV=str(output), IS_BAKASU_COMPAT="true",
                KSUVER="35236", MANAGER_VERSION_CODE="35236"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("无法确认修复版", result.stdout)


class StrictSusfsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
        self.git("init", "-q", "-b", "main")
        (self.repo / "version").write_text("older compatible\n")
        self.git("add", "-A"); self.git("commit", "-qm", "older")
        self.older = self.git("rev-parse", "HEAD")
        (self.repo / "version").write_text("newest\n")
        self.git("add", "-A"); self.git("commit", "-qm", "latest")
        self.latest = self.git("rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, check=True,
                              text=True, capture_output=True).stdout.strip()

    def selection(self, compatible):
        source = WF.read_text()
        a = source.index("            # --- 选择 SUSFS 提交 ---")
        b = source.index("            SUSFS_VER=", a)
        script = ("susfs_ok() { [[ $(git rev-parse HEAD) == $COMPATIBLE ]]; }\n"
                  "SUSFS_AUTO=false; SUSFS_STRICT=true; SUSFS_META=''; SUSFS_NOTE=''\n"
                  + textwrap.dedent(source[a:b]))
        return bash(script, {**self.env, "COMPATIBLE": compatible, "STABLE_SUSFS_COMMIT": self.older}, cwd=self.repo)

    def test_compatible_latest_is_used_without_checkout(self):
        result = self.selection(self.latest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.latest)

    def test_incompatible_latest_stops_instead_of_silently_rolling_back(self):
        result = self.selection(self.older)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不会悄悄回退", result.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.latest)

    def test_new_mode_does_not_enable_legacy_auto_rollback(self):
        source = WF.read_text()
        a = source.index("            STABLE_SUSFS_COMMIT=")
        b = source.index("            git clone https://gitlab.com/simonpunk/susfs4ksu.git", a)
        script = textwrap.dedent(source[a:b]).replace("${{ github.event.inputs.SUSFS_DEV }}", "false")
        result = bash(script + '\nprintf "__MODE__=%s|%s" "$SUSFS_AUTO" "$SUSFS_STRICT"', dict(
            IS_BAKASU_COMPAT="true", SUSFS_META=""))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.endswith("__MODE__=false|true"), result.stdout)


class ProvenanceTests(unittest.TestCase):
    def test_only_whitelisted_non_secret_metadata_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Image").write_bytes(b"kernel image fixture")
            (root / "manager.apk").write_bytes(b"APK fixture")
            result = provenance(root, {
                "IS_BAKASU_COMPAT": "true", "KSU_SHA": "a" * 40,
                "KSU_MANAGER_SHA": "b" * 40, "SUSFS_FULL_SHA": "c" * 40,
                "BAKASU_INIT_MODE": "legacy-initrc-no-preinit",
                "GITHUB_TOKEN": "secret-not-to-be-copied", "GH_TOKEN": "another-private-secret",
            })
            output = json.dumps(result)
            self.assertNotIn("secret-not-to-be-copied", output)
            self.assertNotIn("another-private-secret", output)
            self.assertNotIn("GITHUB_TOKEN", output)
            self.assertEqual(result["kernel"]["commit"], "a" * 40)
            self.assertEqual(result["manager"]["source_commit"], "b" * 40)
            self.assertEqual(len(result["kernel"]["image_sha256"]), 64)
            self.assertEqual(result["apks"][0]["file"], "manager.apk")
            self.assertFalse(result["new_preinit_runner_enabled"])


if __name__ == "__main__":
    unittest.main()
