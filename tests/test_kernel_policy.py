"""The fast checks run without root, a compiler, Linux source, or network access."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("kernel_audit", ROOT / "scripts/audit-kernel.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class KernelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def file(self, text, name="config"):
        path = self.work / name
        path.write_text(text)
        return path

    def test_parse_assignments_and_disabled_symbols(self):
        path = self.file('# comment\nCONFIG_A=y\nCONFIG_B=m\n# CONFIG_C is not set\nCONFIG_N=250\nCONFIG_NAME="hello"\n')
        self.assertEqual(audit.parse_config(path),
                         {"CONFIG_A": "y", "CONFIG_B": "m", "CONFIG_C": "n",
                          "CONFIG_N": "250", "CONFIG_NAME": '"hello"'})

    def test_duplicate_symbol_rejected(self):
        path = self.file('CONFIG_A=y\n# CONFIG_A is not set\n')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.parse_config(path)

    def test_invalid_assignment_rejected(self):
        for line in ('CONFIG_A=maybe', 'CONFIG_A=y # inline', 'CONFIG_A="unterminated',
                     '# CONFIG_A is not sett'):
            with self.subTest(line=line), self.assertRaises(ValueError):
                audit.parse_config(self.file(line))

    def test_cross_fragment_override_is_not_silent(self):
        first = self.file('CONFIG_A=y\n', 'first')
        second = self.file('CONFIG_A=m\n', 'second')
        with self.assertRaisesRegex(ValueError, "repeated"):
            audit.load_policy([first, second])

    def test_missing_disabled_symbol_is_valid(self):
        self.assertEqual(audit.compare({"CONFIG_A": "n"}, {}), [])

    def test_missing_feature_or_module_is_an_error(self):
        self.assertEqual(len(audit.compare({"CONFIG_A": "y", "CONFIG_B": "m"}, {})), 2)

    def test_module_cannot_silently_become_builtin(self):
        self.assertEqual(audit.compare({"CONFIG_A": "m"}, {"CONFIG_A": "y"}),
                         [{"symbol": "CONFIG_A", "expected": "m", "actual": "y"}])

    def test_source_lookup_understands_menuconfig(self):
        self.file('config FIRST\nmenuconfig SECOND\n\tbool "Example"\n', 'Kconfig')
        self.assertEqual(audit.defined_symbols(self.work), {"CONFIG_FIRST", "CONFIG_SECOND"})

    def test_empty_source_tree_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No upstream Kconfig"):
            audit.defined_symbols(self.work)

    def test_policy_is_unambiguous_and_has_core_safety_features(self):
        policy = audit.load_policy(audit.FRAGMENTS)
        for symbol in ('CPU_MITIGATIONS', 'RANDOMIZE_BASE', 'SECCOMP', 'HARDENED_USERCOPY',
                       'DRM_I915', 'SQUASHFS', 'BLK_DEV_SR', 'SERIAL_8250_CONSOLE', 'SUSPEND', 'MEMCG'):
            self.assertEqual(policy['CONFIG_' + symbol], 'y', symbol)
        self.assertEqual(policy['CONFIG_NETFILTER'], 'y')
        for symbol in ('ZRAM', 'WIREGUARD', 'NF_TABLES', 'DM_CRYPT', 'CRYPTO_XTS', 'EXFAT_FS',
                       'NFT_FIB_IPV4', 'NFT_FIB_IPV6', 'NFT_FIB_INET'):
            self.assertEqual(policy['CONFIG_' + symbol], 'm', symbol)
        self.assertEqual(policy['CONFIG_HZ_250'], 'y')
        self.assertEqual(policy['CONFIG_MODULE_FORCE_UNLOAD'], 'n')

    def test_cli_writes_a_failure_report_and_returns_nonzero(self):
        policy = audit.load_policy(audit.FRAGMENTS)
        policy['CONFIG_NETFILTER'] = 'n'
        config = self.file(''.join(f'{key}={value}\n' for key, value in policy.items()))
        report = self.work / 'audit.json'
        result = subprocess.run(['python3', str(ROOT / 'scripts/audit-kernel.py'),
                                 '--config', str(config), '--report', str(report)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('CONFIG_NETFILTER', result.stderr)
        self.assertFalse(json.loads(report.read_text())['passed'])

    def test_cli_accepts_exact_policy_fixture(self):
        policy = audit.load_policy(audit.FRAGMENTS)
        config = self.file(''.join(f'{key}={value}\n' for key, value in policy.items()))
        result = subprocess.run(['python3', str(ROOT / 'scripts/audit-kernel.py'),
                                 '--config', str(config)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_zram_userspace_matches_kernel_and_is_capped(self):
        overlay = ROOT / 'live-build/config/includes.chroot'
        config = (overlay / 'etc/systemd/zram-generator.conf').read_text()
        self.assertIn('zram-size = min(ram / 2, 2048)', config)
        self.assertIn('compression-algorithm = lz4', config)
        packages = (ROOT / 'live-build/config/package-lists/znlite.list.chroot').read_text().splitlines()
        for package in ('systemd-zram-generator', 'nftables', 'wireguard-tools', 'apparmor',
                        'cryptsetup-initramfs', 'exfatprogs'):
            self.assertIn(package, packages)

    def test_doctor_is_read_only_and_runs_without_root(self):
        result = subprocess.run([str(ROOT / 'live-build/config/includes.chroot/usr/local/bin/znlite'),
                                 'doctor'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No settings were changed', result.stdout)
        self.assertIn('Compressed RAM swap', result.stdout)


if __name__ == '__main__':
    unittest.main()
