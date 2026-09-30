#!/usr/bin/python3
"""Opt-out boot-time mirror measurement; only Znlite-owned APT sources may change.

Standard library only. TLS and Debian signatures remain mandatory. Measurements
are samples, not a global fastest-mirror guarantee. No packages are installed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

SUITES = ('trixie', 'trixie-updates', 'trixie-backports')
KEYRING = '/usr/share/keyrings/debian-archive-keyring.gpg'
DEFAULT_MIRROR = 'https://deb.debian.org/debian'
DEFAULTS = {
    'enabled': True,
    'candidates': [DEFAULT_MIRROR, 'https://ftp.debian.org/debian',
                   'https://mirrors.kernel.org/debian',
                   'https://mirror.csclub.uwaterloo.ca/debian'],
}
OWNER = '# Managed by Znlite mirror selection. Editing this file freezes automatic changes.\n'


def normalize_url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('Mirror must be a whitespace-free HTTPS URL')
    url = urlparse(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.params):
        raise ValueError('Mirror must use HTTPS without credentials, query or fragment')
    return value.rstrip('/')


class SecureRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        normalize_url(newurl)  # Never follow a TLS downgrade, even for a sample.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, limit, sample=False):
    """Bound each response by bytes and a wall-clock deadline; no unbounded read."""
    normalize_url(url)
    headers = {'User-Agent': 'Znlite-Mirror-Selector/1', 'Accept-Encoding': 'identity'}
    if sample:
        headers['Range'] = f'bytes=0-{limit - 1}'
    request = Request(url, headers=headers)
    start = time.monotonic()
    chunks = []
    total = 0
    with build_opener(HTTPSHandler(), SecureRedirect()).open(request, timeout=2) as response:
        normalize_url(response.url)
        while total < limit:
            if time.monotonic() - start > 5:
                raise TimeoutError('Mirror sample deadline exceeded')
            chunk = response.read1(min(32768, limit - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if not sample and total == limit:
            raise ValueError('Oversized repository metadata')
    return b''.join(chunks), max(time.monotonic() - start, 0.001)


def release_fields(payload):
    # Read only the clear-signed message, not headers or the signature packet.
    text = payload.decode('utf-8')
    if not text.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
        raise ValueError('Not a signed InRelease document')
    body = text.split('\n\n', 1)[1].split('-----BEGIN PGP SIGNATURE-----', 1)[0]
    return dict(line.split(': ', 1) for line in body.splitlines()
                if ': ' in line and not line.startswith(' '))


def verify_metadata(payload, suite, directory, now=None):
    path = directory / 'InRelease'
    path.write_bytes(payload)
    subprocess.run(['gpgv', '--keyring', KEYRING, str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=5)
    fields = release_fields(payload)
    now = now or datetime.now(timezone.utc)
    if fields.get('Origin') != 'Debian' or fields.get('Codename') != suite:
        raise ValueError(f'Wrong repository identity for {suite}')
    issued = parsedate_to_datetime(fields['Date'])
    if issued.tzinfo is None or issued > now + timedelta(hours=24):
        raise ValueError('Invalid repository date or system clock')
    if 'Valid-Until' in fields:
        expiry = parsedate_to_datetime(fields['Valid-Until'])
        if expiry.tzinfo is None or expiry < now:
            raise ValueError('Expired repository metadata')
    elif suite != 'trixie':
        raise ValueError('Updates/backports metadata must have an expiry')
    # Confirm that the sample path actually belongs to this signed repository.
    if b'main/binary-amd64/Packages.xz' not in payload:
        raise ValueError('No amd64 package index advertised')


def probe(mirror):
    mirror = normalize_url(mirror)
    elapsed = 0.0
    with tempfile.TemporaryDirectory(prefix='znlite-mirror-') as directory:
        for suite in SUITES:
            payload, duration = download(f'{mirror}/dists/{suite}/InRelease', 512 * 1024)
            verify_metadata(payload, suite, Path(directory))
            elapsed += duration
        # A small throughput sample, not an installation source or executable.
        # APT independently verifies hashes of complete indexes and packages.
        payload, duration = download(f'{mirror}/dists/trixie/main/binary-amd64/Packages.xz',
                                     256 * 1024, sample=True)
        if len(payload) != 256 * 1024 or not payload.startswith(b'\xfd7zXZ\x00'):
            raise ValueError('Incomplete or invalid package-index sample')
        elapsed += duration
    return {'mirror': mirror, 'seconds': round(elapsed, 6), 'sample_bytes': len(payload)}


def sources(mirror):
    mirror = normalize_url(mirror)
    return OWNER + f'''Types: deb
URIs: {mirror}
Suites: trixie trixie-updates trixie-backports
Components: main contrib non-free non-free-firmware
Signed-By: {KEYRING}

Types: deb
URIs: https://security.debian.org/debian-security
Suites: trixie-security
Components: main contrib non-free non-free-firmware
Signed-By: {KEYRING}
'''


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.znlite-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), 0o644)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Manager:
    def __init__(self, root=Path('/')):
        self.root = root
        self.apt = root / 'etc/apt'
        self.managed = self.apt / 'sources.list.d/znlite.sources'
        self.state = root / 'var/lib/znlite-mirrors/owner.json'
        self.report = root / 'var/lib/znlite-mirrors/last-run.json'
        self.config = root / 'etc/znlite/mirrors.json'

    def settings(self):
        value = json.loads(self.config.read_text())
        candidates = value.get('candidates')
        if type(value.get('enabled')) is not bool:
            raise ValueError('enabled must be true or false')
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= 8:
            raise ValueError('Configure between 1 and 8 mirror candidates')
        value['candidates'] = list(dict.fromkeys(normalize_url(x) for x in candidates))
        return value

    def source_files(self):
        return [self.apt / 'sources.list',
                *sorted((self.apt / 'sources.list.d').glob('*.list')),
                *sorted((self.apt / 'sources.list.d').glob('*.sources'))]

    def may_change(self):
        if self.managed.is_symlink() or not self.managed.is_file() or not self.state.is_file():
            return False
        owner = json.loads(self.state.read_text())
        if digest(self.managed.read_text()) != owner.get('sha256'):
            return False
        # Conservative ownership rule: any additional active repository freezes
        # automatic selection, even if its contents happen to be Debian too.
        for path in self.source_files():
            if path == self.managed or not path.exists():
                continue
            if any(line.strip() and not line.lstrip().startswith('#')
                   for line in path.read_text().splitlines()):
                return False
        return True

    def save_selection(self, mirror):
        if not self.may_change():
            raise ValueError('APT sources are user-managed; automatic changes refused')
        content = sources(mirror)
        if self.managed.read_text() == content:
            return False
        atomic_write(self.managed, content)
        # If power fails between these writes, the mismatch freezes future edits.
        atomic_write(self.state, json.dumps({'sha256': digest(content), 'mirror': mirror}) + '\n')
        return True

    def initialize_image(self):
        """Build-only adoption, not exposed as a user command. Reject custom repos."""
        if self.state.exists() or self.managed.exists():
            raise ValueError('Image sources have already been initialized')
        existing = []
        for path in self.source_files():
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                # live-build's known Debian .list files only. Do not silently
                # remove arbitrary Deb822 repositories or third-party entries.
                import re
                match = re.fullmatch(r'deb(?:-src)?\s+(?:\[[^\]]+\]\s+)?'
                                     r'(https?://(?:deb\.debian\.org/debian(?:-security)?|'
                                     r'security\.debian\.org(?:/debian-security)?)/?)\s+'
                                     r'(trixie(?:-updates|-security|-backports)?)\s+'
                                     r'(?:main|contrib|non-free|non-free-firmware)'
                                     r'(?:\s+(?:main|contrib|non-free|non-free-firmware))*\s*', line)
                if not match:
                    raise ValueError(f'Unexpected build repository in {path}: {line}')
            existing.append(path)
        for path in existing:
            atomic_write(path, '# Replaced by Znlite-owned sources.list.d/znlite.sources\n')
        content = sources(DEFAULT_MIRROR)
        atomic_write(self.managed, content)
        atomic_write(self.state, json.dumps({'sha256': digest(content), 'mirror': DEFAULT_MIRROR}) + '\n')
        atomic_write(self.config, json.dumps(DEFAULTS, indent=2) + '\n')

    @contextmanager
    def lock(self):
        lock = self.root / 'run/znlite-mirrors.lock'
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open('a') as own:
            fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    @contextmanager
    def apt_lock(self):
        # Only lock APT for the final write, not while testing network speeds.
        path = self.root / 'var/lib/apt/lists/lock'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as apt:
            fcntl.lockf(apt, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def select(self, probe_fn=probe):
        config = self.settings()
        if not config['enabled']:
            print('Automatic mirror selection is disabled; no changes made.')
            return
        with self.lock():
            if not self.may_change():
                raise ValueError('Custom APT sources detected; no changes made')
            results, errors = [], []
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(probe_fn, url): url for url in config['candidates']}
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as error:
                        errors.append({'mirror': futures[future], 'error': str(error)[:250]})
            results.sort(key=lambda result: (result['seconds'], result['mirror']))
            report = {'measured_at': datetime.now(timezone.utc).isoformat(),
                      'results': results, 'errors': errors, 'changed': False}
            if results:
                with self.apt_lock():
                    report['changed'] = self.save_selection(results[0]['mirror'])
                print(f"Selected fastest valid sample: {results[0]['mirror']}")
            else:
                print('No valid reachable candidates; keeping previous APT sources.')
            atomic_write(self.report, json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('select')
    auto = sub.add_parser('auto')
    auto.add_argument('mode', choices=('on', 'off'))
    args = parser.parse_args()
    manager = Manager()
    try:
        if args.command == 'status':
            print(json.dumps(manager.settings(), indent=2))
            print('APT ownership:', 'Znlite-managed' if manager.may_change() else 'custom/uninitialized (frozen)')
            if manager.report.exists():
                print(manager.report.read_text())
        else:
            if os.geteuid() != 0:
                parser.error('Run with sudo')
            if args.command == 'auto':
                with manager.lock():
                    config = manager.settings()
                    config['enabled'] = args.mode == 'on'
                    atomic_write(manager.config, json.dumps(config, indent=2) + '\n')
                print(f'Automatic mirror selection: {args.mode}')
            else:
                manager.select()
    except (OSError, ValueError, KeyError) as error:
        print(f'Mirror selection: {error}. Selection did not complete; inspect znlite mirror status.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
