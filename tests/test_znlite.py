"""Znlite user commands: no network, root access, package installs, or GPU needed."""
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "live-build/config/includes.chroot"
BIN = OVERLAY / "usr/local/bin"
SHARE = OVERLAY / "usr/local/share/znlite"


def run(*args, env=None):
    return subprocess.run(
        args, env={**os.environ, **(env or {})},
        capture_output=True, text=True, timeout=10,
    )


class FetchTests(unittest.TestCase):
    def test_piped_output_has_info_and_no_escape_codes(self):
        result = run(str(BIN / "znfetch"))
        self.assertEqual(result.returncode, 0, result.stderr)
        for label in ("OS", "Kernel", "Uptime", "Packages", "CPU", "Memory", "Disk"):
            self.assertIn(label, result.stdout)
        self.assertNotIn("\x1b", result.stdout)

    def test_full_mascot_preserves_supplied_art(self):
        result = run(str(BIN / "znfetch"), "--logo-only", "--no-color")
        self.assertEqual(result.stdout, (SHARE / "mascot.txt").read_text())

    def test_truecolor_can_be_forced_without_changing_art(self):
        # NO_COLOR is absent in the normal test environment.
        result = run(str(BIN / "znfetch"), "--logo-only", "--color=always",
                     env={"TERM": "xterm-256color", "COLORTERM": "truecolor"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\x1b[38;2;", result.stdout)
        self.assertEqual(re.sub(r"\x1b\[[0-9;]*m", "", result.stdout),
                         (SHARE / "mascot.txt").read_text())

    def test_linux_console_uses_ansi_not_truecolor(self):
        result = run(str(BIN / "znfetch"), "--logo-only", "--color=always",
                     env={"TERM": "linux", "COLORTERM": ""})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\x1b[1;36m", result.stdout)
        self.assertNotIn("38;2;", result.stdout)

    def test_no_color_overrides_forcing(self):
        result = run(str(BIN / "znfetch"), "--color=always",
                     env={"NO_COLOR": "", "TERM": "xterm-256color"})
        self.assertNotIn("\x1b", result.stdout)

    def test_dumb_terminal_disables_effects(self):
        result = run(str(BIN / "znfetch"), "--color=always", "--animate", env={"TERM": "dumb"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b", result.stdout)

    def test_neofetch_command_uses_the_mascot(self):
        result = run(str(BIN / "neofetch"), "--logo-only", "--no-color")
        self.assertEqual(result.stdout, (SHARE / "mascot.txt").read_text())

    def test_unknown_option_is_rejected(self):
        result = run(str(BIN / "znfetch"), "--made-up")
        self.assertEqual(result.returncode, 2)

    def test_noninteractive_profile_is_silent(self):
        result = run("bash", "-c", '. "$1"; printf ok', "bash",
                     str(OVERLAY / "etc/profile.d/znlite.sh"))
        self.assertEqual(result.stdout, "ok")
        self.assertEqual(result.returncode, 0, result.stderr)


class UpdateTests(unittest.TestCase):
    def update(self, *options, live=False, fail_refresh=False):
        # Source definitions, then replace only privileged/environment operations.
        # APT is ALWAYS a function here, so tests can never change host packages.
        script = '''
source "$1"
shift
require_root() { :; }
is_live() { [[ $TEST_LIVE == 1 ]]; }
apt-get() {
    printf 'APT:'
    printf ' <%s>' "$@"
    printf '\\n'
    if [[ $TEST_FAIL_REFRESH == 1 && $* == *Error-Mode=any* ]]; then return 100; fi
}
main update "$@"
'''
        return run("bash", "-c", script, "bash", str(BIN / "znlite"), *options,
                   env={"TEST_LIVE": str(int(live)), "TEST_FAIL_REFRESH": str(int(fail_refresh))})

    def test_default_upgrade_preserves_confirmation(self):
        result = self.update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<APT::Update::Error-Mode=any> <update>", result.stdout)
        self.assertIn("APT: <full-upgrade>", result.stdout)
        self.assertNotIn("--assume-yes", result.stdout)
        self.assertIn("Custom Znlite kernel/tools are not covered", result.stdout)

    def test_check_simulates_without_upgrade(self):
        result = self.update("--check", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("APT: <--simulate> <full-upgrade>", result.stdout)
        self.assertNotIn("--assume-yes", result.stdout)

    def test_yes_is_explicit(self):
        result = self.update("--yes")
        self.assertIn("APT: <--assume-yes> <full-upgrade>", result.stdout)

    def test_live_session_is_refused_before_apt(self):
        result = self.update(live=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("APT:", result.stdout)
        self.assertIn("--allow-live", result.stderr)

    def test_live_session_requires_opt_in_and_warns(self):
        result = self.update("--allow-live", live=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("may not persist", result.stderr)
        self.assertIn("APT: <full-upgrade>", result.stdout)

    def test_failed_index_refresh_never_upgrades(self):
        result = self.update(fail_refresh=True)
        self.assertEqual(result.returncode, 100)
        self.assertNotIn("full-upgrade", result.stdout)

    def test_invalid_flag_never_runs_apt(self):
        result = self.update("--unsafe")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("APT:", result.stdout)

    @unittest.skipIf(os.geteuid() == 0, "Test requires an unprivileged caller")
    def test_unprivileged_user_is_refused(self):
        result = run(str(BIN / "znlite"), "update")
        self.assertEqual(result.returncode, 1)
        self.assertIn("sudo", result.stderr)


class ConsoleTests(unittest.TestCase):
    def console(self, mode="vector", video=True, result=1):
        script = '''
. "$1"
znlite_console_mode() { printf '%s' "$TEST_MODE"; }
znlite_has_video() { test "$TEST_VIDEO" = 1; }
kmscon() { :; }
znlite_start_vector() { echo VECTOR; return "$TEST_RESULT"; }
znlite_start_raster() { echo RASTER; }
znlite_console
'''
        return run("sh", "-c", script, "sh", str(SHARE / "console.sh"),
                   env={"TEST_MODE": mode, "TEST_VIDEO": str(int(video)), "TEST_RESULT": str(result)})

    def test_vector_failure_falls_back(self):
        result = self.console()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "VECTOR\nRASTER\n")

    def test_vector_clean_exit_also_keeps_login_available(self):
        result = self.console(result=0)
        self.assertEqual(result.stdout, "VECTOR\nRASTER\n")

    def test_no_video_uses_raster_immediately(self):
        result = self.console(video=False)
        self.assertEqual(result.stdout, "RASTER\n")

    def test_raster_preference_skips_vector(self):
        result = self.console(mode="raster")
        self.assertEqual(result.stdout, "RASTER\n")

    def test_invalid_preference_is_safe(self):
        result = self.console(mode="not-a-mode")
        self.assertEqual(result.stdout, "RASTER\n")

    def test_boot_menu_offers_rescue_on_both_firmware_types(self):
        boot = ROOT / "live-build/config/bootloaders"
        for config in ("syslinux_common/live.cfg.in", "grub-pc/grub.cfg"):
            self.assertIn("znlite.console=raster", (boot / config).read_text())

    def test_vector_is_default_and_rescue_getty_is_enabled(self):
        self.assertEqual((OVERLAY / "etc/znlite/console-mode").read_text().strip(), "vector")
        hook = ROOT / "live-build/config/hooks/live/0500-znlite.hook.chroot"
        self.assertIn("getty@tty2.service", hook.read_text())
        self.assertIn("font-engine=freetype", (OVERLAY / "etc/kmscon/kmscon.conf").read_text())


if __name__ == "__main__":
    unittest.main()
