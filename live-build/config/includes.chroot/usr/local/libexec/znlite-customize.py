#!/usr/bin/python3
"""Copy editable defaults without clobbering user files; switch reversible presets."""
import argparse
import os
from pathlib import Path
import sys

DEFAULTS = Path('/etc/xdg/znlite')
FILES = ('sway/config', 'foot/foot.ini', 'waybar/config', 'waybar/style.css',
         'fuzzel/fuzzel.ini', 'mako/config', 'gtk-3.0/settings.ini')
PRESETS = {
    'aurora': '# Managed by znlite customize preset\ngaps inner 8\ngaps outer 4\ndefault_border pixel 2\n',
    'minimal': '# Managed by znlite customize preset\ngaps inner 0\ngaps outer 0\ndefault_border pixel 1\n',
}


def initialize(defaults, destination):
    for relative in FILES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Exclusive creation: even a dangling symlink counts as user-owned.
            with target.open('x') as output:
                output.write((defaults / relative).read_text())
            print(f'Created {target}')
        except FileExistsError:
            print(f'Kept existing {target}')


def preset(destination, name):
    target = destination / 'znlite/preset.conf'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError(f'Refusing to overwrite symlink: {target}')
    if target.exists() and target.read_text() not in PRESETS.values():
        raise ValueError(f'{target} has custom changes; move it aside first.')
    target.write_text(PRESETS[name])
    print(f'Preset: {name}. Reload Sway with Super+Shift+C.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    p = sub.add_parser('preset')
    p.add_argument('name', choices=PRESETS)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as your desktop user, not with sudo.')
    destination = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    if not destination.is_absolute():
        parser.error('XDG_CONFIG_HOME must be an absolute path')
    try:
        if args.command == 'init':
            initialize(DEFAULTS, destination)
        else:
            preset(destination, args.name)
        print(f'Your files live in {destination}. Edit freely; no reboot needed.')
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
