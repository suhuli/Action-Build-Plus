"""Run dependency/cache shell steps with mocks, without sudo or network."""
import tempfile
import unittest
from pathlib import Path

from test_bakasu_pin import WF, bash, step_script


class DependencyTests(unittest.TestCase):
    def run_install(self, missing=""):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "commands"
            mocks = r'''
            sudo() { printf 'sudo %s\n' "$*" >> "$COMMAND_LOG"; }
            command() {
              if [[ "$1" == -v ]]; then
                [[ "$2" != "$MISSING_TOOL" ]]
              else
                builtin command "$@"
              fi
            }
            ccache() { printf 'ccache %s\n' "$*" >> "$COMMAND_LOG"; }
            '''
            result = bash(mocks + step_script("Install Build Dependencies"), dict(
                COMMAND_LOG=str(log), MISSING_TOOL=missing))
            return result, log.read_text() if log.exists() else ""

    def test_required_tools_are_really_installed_not_only_cached(self):
        result, log = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sudo apt-get update", log)
        install = next(line for line in log.splitlines() if "apt-get install" in line)
        self.assertIn("ccache", install)
        self.assertIn("build-essential", install)
        self.assertIn("bc", install)
        self.assertIn("ccache --version", log)
        self.assertNotIn("cache-apt-pkgs-action@", WF.read_text())

    def test_incomplete_install_fails_before_build(self):
        result, _ = self.run_install(missing="ccache")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Required tool ccache is still missing", result.stdout)

    def test_legacy_production_environment_is_pinned(self):
        self.assertIn("runs-on: ubuntu-22.04", WF.read_text())


class CcacheInitializationTests(unittest.TestCase):
    def run_init(self, present=True, initialized=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "cache dir"
            log = root / "commands"
            if initialized:
                cache.mkdir()
                (cache / ".ccache_initialized").touch()
            script = step_script("Initialize Ccache")
            script = script.replace("${{ env.CCACHE_DIR }}", str(cache))
            script = script.replace("${{ env.CCACHE_MAXSIZE }}", "15G")
            mocks = r'''
            command() {
              if [[ "$1" == -v && "$2" == ccache ]]; then
                [[ "$CCACHE_PRESENT" == yes ]]
              else
                builtin command "$@"
              fi
            }
            ccache() { printf '%s\n' "$*" >> "$COMMAND_LOG"; }
            '''
            result = bash(mocks + script, dict(
                COMMAND_LOG=str(log), CCACHE_PRESENT="yes" if present else "no"))
            return result, log.read_text() if log.exists() else "", (cache / ".ccache_initialized").exists()

    def test_first_run_initializes_and_prints_stats(self):
        result, log, flag = self.run_init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-M 15G", log)
        self.assertIn("-s", log)
        self.assertTrue(flag)

    def test_restored_cache_is_not_reinitialized(self):
        result, log, _ = self.run_init(initialized=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("-M", log)
        self.assertIn("-s", log)

    def test_missing_ccache_is_an_explicit_error_not_false_skip(self):
        result, log, flag = self.run_init(present=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Required ccache executable is missing", result.stdout)
        self.assertEqual(log, "")
        self.assertFalse(flag)


if __name__ == "__main__":
    unittest.main()
