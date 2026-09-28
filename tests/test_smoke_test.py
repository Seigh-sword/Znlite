"""Exercise the smoke-test wrapper without building an ISO or starting a VM."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SmokeTestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.iso = self.work / "test image.iso"
        self.iso.touch()
        self.log = self.work / "logs" / "boot.log"
        self.args = self.work / "qemu-args"
        self.timeout_args = self.work / "timeout-args"
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "QEMU_TIMEOUT": "300",
            "TEST_QEMU_ARGS": str(self.args),
            "TEST_TIMEOUT_ARGS": str(self.timeout_args),
            "TEST_SERIAL": "znlite login: ",
            "TEST_STDERR": "",
            "TEST_STATUS": "124",
        }
        self.executable(
            "timeout",
            '#!/bin/sh\nprintf "%s\\n" "$@" > "$TEST_TIMEOUT_ARGS"\n'
            'shift 2\nexec "$@"\n',
        )
        self.executable(
            "qemu-system-x86_64",
            '''#!/bin/sh
printf '%s\n' "$@" > "$TEST_QEMU_ARGS"
while [ "$#" -gt 0 ]; do
    if [ "$1" = '-serial' ]; then
        shift
        printf '%s\n' "$TEST_SERIAL" >> "${1#file:}"
    fi
    shift
done
printf '%s\n' "$TEST_STDERR" >&2
exit "$TEST_STATUS"
''',
        )

    def executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_smoke(self, **env):
        return subprocess.run(
            [str(ROOT / "scripts/smoke-test.sh"), str(self.iso), str(self.log)],
            env={**self.env, **env},
            text=True,
            capture_output=True,
            timeout=5,
        )

    def test_timeout_after_login_is_success(self):
        result = self.run_smoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reached the Znlite text login prompt", result.stdout)

    def test_clean_exit_after_login_is_success(self):
        result = self.run_smoke(TEST_STATUS="0")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_headless_arguments_and_default_timeout(self):
        result = self.run_smoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.args.read_text().splitlines()
        for flag, value in (
            ("-accel", "tcg"),
            ("-display", "none"),
            ("-monitor", "none"),
            ("-audiodev", "none,id=audio0"),
            ("-cdrom", str(self.iso)),
            ("-serial", f"file:{self.log}"),
        ):
            self.assertEqual(args[args.index(flag) + 1], value)
        self.assertEqual(
            self.timeout_args.read_text().splitlines()[:2],
            ["--kill-after=10s", "300s"],
        )

    def test_custom_timeout(self):
        result = self.run_smoke(QEMU_TIMEOUT="12")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.timeout_args.read_text().splitlines()[1], "12s")

    def test_invalid_timeout_does_not_launch_qemu(self):
        for value in ("0", "00", "-1", "invalid", "1.5"):
            with self.subTest(value=value):
                result = self.run_smoke(QEMU_TIMEOUT=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("positive number", result.stderr)
                self.assertFalse(self.args.exists())

    def test_missing_iso_does_not_launch_qemu(self):
        self.iso.unlink()
        result = self.run_smoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing ISO image", result.stderr)
        self.assertFalse(self.args.exists())

    def test_banner_without_login_fails(self):
        result = self.run_smoke(TEST_SERIAL="Znlite Linux text-only live system")
        self.assertEqual(result.returncode, 1)
        self.assertIn("did not reach a text login prompt", result.stderr)

    def test_empty_serial_log_fails_and_reports_stderr(self):
        result = self.run_smoke(TEST_SERIAL="", TEST_STDERR="QEMU diagnostic")
        self.assertEqual(result.returncode, 1)
        self.assertIn("QEMU diagnostic", result.stderr)

    def test_qemu_error_is_preserved_even_with_login_text(self):
        result = self.run_smoke(TEST_STATUS="42", TEST_STDERR="QEMU launch failed")
        self.assertEqual(result.returncode, 42)
        self.assertIn("QEMU launch failed", result.stderr)

    def test_forced_kill_is_not_a_success(self):
        result = self.run_smoke(TEST_STATUS="137")
        self.assertEqual(result.returncode, 137)

    def test_stale_login_log_cannot_mask_failure(self):
        self.log.parent.mkdir()
        self.log.write_text("znlite login: ")
        result = self.run_smoke(TEST_SERIAL="")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("login:", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
