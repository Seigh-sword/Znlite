import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'live-build/config/includes.chroot'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, OVERLAY / 'usr/local/libexec' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mirrors = load('mirrors', 'znlite-mirrors.py')
customize = load('customize', 'znlite-customize.py')


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = mirrors.Manager(self.root)
        self.manager.apt.mkdir(parents=True)
        (self.manager.apt / 'sources.list').write_text('deb http://deb.debian.org/debian trixie main\n')
        self.manager.initialize_image()

    def test_initial_sources_are_signed_and_security_is_fixed(self):
        text = self.manager.managed.read_text()
        self.assertTrue(self.manager.may_change())
        self.assertIn('https://security.debian.org/debian-security', text)
        self.assertEqual(text.count('Signed-By:'), 2)
        self.assertNotIn('Trusted: yes', text)

    def test_only_owned_sources_change(self):
        before = (self.manager.apt / 'sources.list').read_text()
        self.manager.save_selection('https://example.org/debian')
        self.assertEqual((self.manager.apt / 'sources.list').read_text(), before)
        self.assertIn('https://security.debian.org/debian-security', self.manager.managed.read_text())

    def test_modified_managed_file_is_never_overwritten(self):
        self.manager.managed.write_text('My custom repository configuration\n')
        with self.assertRaises(ValueError):
            self.manager.save_selection(mirrors.DEFAULT_MIRROR)
        self.assertEqual(self.manager.managed.read_text(), 'My custom repository configuration\n')

    def test_additional_repository_freezes_selection(self):
        path = self.manager.apt / 'sources.list.d/custom.list'
        path.write_text('deb https://custom.example stable main\n')
        self.assertFalse(self.manager.may_change())
        with self.assertRaises(ValueError):
            self.manager.select(lambda url: self.fail('Must not probe custom setups'))

    def test_managed_symlink_is_not_followed(self):
        self.manager.managed.unlink()
        target = self.root / 'precious'
        target.write_text('untouched')
        self.manager.managed.symlink_to(target)
        self.assertFalse(self.manager.may_change())
        self.assertEqual(target.read_text(), 'untouched')

    def test_disabled_setting_makes_no_network_calls(self):
        config = self.manager.settings()
        config['enabled'] = False
        self.manager.config.write_text(json.dumps(config))
        self.manager.select(lambda url: self.fail('Network call while disabled'))

    def test_offline_boot_preserves_last_working_source(self):
        before = self.manager.managed.read_bytes()
        def offline(url):
            raise OSError('offline')
        self.manager.select(offline)
        self.assertEqual(self.manager.managed.read_bytes(), before)
        self.assertFalse(json.loads(self.manager.report.read_text())['changed'])

    def test_fastest_successful_sample_wins(self):
        candidates = self.manager.settings()['candidates']
        def measure(url):
            if url == candidates[0]:
                raise ValueError('invalid signature')
            return {'mirror': url, 'seconds': candidates.index(url), 'sample_bytes': 262144}
        self.manager.select(measure)
        self.assertIn(candidates[1], self.manager.managed.read_text())
        self.assertEqual(len(json.loads(self.manager.report.read_text())['errors']), 1)

    def test_source_change_during_measurement_aborts_commit(self):
        def change(url):
            self.manager.managed.write_text('changed by admin')
            return {'mirror': url, 'seconds': 1}
        with self.assertRaises(ValueError):
            self.manager.select(change)
        self.assertEqual(self.manager.managed.read_text(), 'changed by admin')

    def test_initializer_rejects_unknown_repository_before_editing(self):
        with tempfile.TemporaryDirectory() as root:
            manager = mirrors.Manager(Path(root))
            manager.apt.mkdir(parents=True)
            path = manager.apt / 'sources.list'
            path.write_text('deb https://third.party.example stable main\n')
            with self.assertRaises(ValueError):
                manager.initialize_image()
            self.assertIn('third.party.example', path.read_text())
            self.assertFalse(manager.managed.exists())

    def test_invalid_urls_rejected(self):
        for url in ('http://example.com/debian', 'file:///etc/passwd',
                    'https://user:pass@example.com', 'https://example.com\nTrusted: yes',
                    'https://example.com#fragment', 'https://example.com?q=1'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                mirrors.normalize_url(url)

    def test_tls_downgrade_redirect_rejected(self):
        with self.assertRaises(ValueError):
            mirrors.SecureRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com')

    def test_corrupt_owner_state_fails_closed(self):
        self.manager.state.write_text('not json')
        with self.assertRaises(ValueError):
            self.manager.select(lambda url: self.fail('Must not probe corrupt state'))

    def test_apt_lock_blocks_write_without_blocking_probes(self):
        # APT uses process-associated POSIX locks; use a separate process.
        path = self.root / 'var/lib/apt/lists/lock'
        path.parent.mkdir(parents=True)
        script = 'import fcntl,sys; f=open(sys.argv[1],"a"); fcntl.lockf(f,fcntl.LOCK_EX); print("ready",flush=True); sys.stdin.read()'
        process = subprocess.Popen(['python3', '-c', script, str(path)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            before = self.manager.managed.read_bytes()
            with self.assertRaises(BlockingIOError):
                self.manager.select(lambda url: {'mirror': url, 'seconds': 1})
            self.assertEqual(self.manager.managed.read_bytes(), before)
        finally:
            process.communicate('', timeout=5)


class MetadataTests(unittest.TestCase):
    def payload(self, suite='trixie', expired=False, origin='Debian', future=False):
        now = datetime.now(timezone.utc)
        date = now + timedelta(days=3) if future else now - timedelta(hours=1)
        expiry = now + timedelta(days=-1 if expired else 7)
        return (f'-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\nOrigin: {origin}\n'
                f'Codename: {suite}\nDate: {format_datetime(date)}\n'
                f'Valid-Until: {format_datetime(expiry)}\nSHA256:\n abc 123 main/binary-amd64/Packages.xz\n'
                '-----BEGIN PGP SIGNATURE-----\nsignature\n').encode()

    def verify(self, payload, suite='trixie'):
        with tempfile.TemporaryDirectory() as root:
            mirrors.verify_metadata(payload, suite, Path(root))

    @patch.object(mirrors.subprocess, 'run')
    def test_signed_valid_metadata(self, run):
        self.verify(self.payload())
        args = run.call_args[0][0]
        self.assertEqual(args[:3], ['gpgv', '--keyring', mirrors.KEYRING])
        self.assertTrue(run.call_args.kwargs['check'])

    @patch.object(mirrors.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'gpgv'))
    def test_signature_failure_is_fatal(self, run):
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(self.payload())

    @patch.object(mirrors.subprocess, 'run')
    def test_stale_wrong_suite_wrong_origin_and_bad_clock_are_rejected(self, run):
        for payload in (self.payload(expired=True), self.payload(suite='bookworm'),
                        self.payload(origin='Not Debian'), self.payload(future=True)):
            with self.assertRaises(ValueError):
                self.verify(payload)

    @patch.object(mirrors.subprocess, 'run')
    def test_unsigned_page_is_not_accepted(self, run):
        with self.assertRaises(ValueError):
            self.verify(b'<html>captive portal</html>')


class DesktopTests(unittest.TestCase):
    def test_initialization_preserves_user_configs_and_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root)
            (dest / 'sway').mkdir()
            (dest / 'sway/config').write_text('my config')
            (dest / 'foot').mkdir()
            (dest / 'foot/foot.ini').symlink_to(dest / 'missing')
            customize.initialize(OVERLAY / 'etc/xdg/znlite', dest)
            self.assertEqual((dest / 'sway/config').read_text(), 'my config')
            self.assertTrue((dest / 'foot/foot.ini').is_symlink())
            self.assertTrue((dest / 'waybar/config').exists())

    def test_presets_are_reversible_but_do_not_clobber_manual_edits(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root)
            for name in ('minimal', 'aurora', 'minimal'):
                customize.preset(dest, name)
                self.assertEqual((dest / 'znlite/preset.conf').read_text(), customize.PRESETS[name])
            (dest / 'znlite/preset.conf').write_text('my own rules')
            with self.assertRaises(ValueError):
                customize.preset(dest, 'aurora')

    def test_presets_do_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root)
            (dest / 'znlite').mkdir()
            (dest / 'znlite/preset.conf').symlink_to(dest / 'missing')
            with self.assertRaises(ValueError):
                customize.preset(dest, 'aurora')

    def test_waybar_configuration_is_valid_json(self):
        config = json.loads((OVERLAY / 'etc/xdg/znlite/waybar/config').read_text())
        self.assertIn('clock', config['modules-center'])

    def test_rescue_entries_do_not_launch_desktop(self):
        for path in (ROOT / 'live-build/config/bootloaders').rglob('*.cfg*'):
            for line in path.read_text().splitlines():
                if 'znlite.console=raster' in line:
                    self.assertIn('systemd.unit=multi-user.target', line)

    def test_default_greeter_is_not_root_or_autologin(self):
        config = (OVERLAY / 'etc/greetd/config.toml').read_text()
        self.assertIn('user = "_znlite-greeter"', config)
        self.assertNotIn('[initial_session]', config)
        self.assertIn('znlite-session', config)

    def test_mirror_service_is_bounded_and_not_a_login_dependency(self):
        service = (OVERLAY / 'etc/systemd/system/znlite-mirrors.service').read_text()
        self.assertIn('TimeoutStartSec=90', service)
        self.assertNotIn('network-online.target', service)
        self.assertNotIn('Before=graphical.target', service)


class SessionTests(unittest.TestCase):
    def test_existing_user_sway_config_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            sway = bin_dir / 'sway'
            sway.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nprintf "desktop=%s" "$XDG_CURRENT_DESKTOP"\n')
            sway.chmod(0o755)
            config = root / 'custom config/sway'
            config.mkdir(parents=True)
            (config / 'config').write_text('# user owned')
            result = subprocess.run([str(OVERLAY / 'usr/local/bin/znlite-session')],
                                    env={**os.environ, 'PATH': f"{bin_dir}:{os.environ['PATH']}",
                                         'XDG_CONFIG_HOME': str(config.parent),
                                         'DBUS_SESSION_BUS_ADDRESS': 'test-existing-bus'},
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('/etc/xdg/znlite/sway/config', result.stdout)
            self.assertIn('desktop=sway', result.stdout)

    def test_broad_platform_profile_keeps_gpu_vm_and_wifi_drivers(self):
        text = (ROOT / 'kernel/platform.fragment').read_text()
        for symbol in ('DRM_AMDGPU', 'DRM_NOUVEAU', 'DRM_VIRTIO_GPU', 'VIRTIO_BLK',
                       'VIRTIO_NET', 'KVM_INTEL', 'KVM_AMD', 'IWLMVM', 'IWLDVM'):
            self.assertIn(f'CONFIG_{symbol}=m', text)
