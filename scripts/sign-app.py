#!/usr/bin/env python3
"""Sign nested executables inside-out, then seal the application."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def configuration():
    config = json.loads((ROOT / 'release/config.json').read_text())
    local = ROOT / '.release/local.json'
    if local.exists():
        config.update(json.loads(local.read_text()))
    config['signing_identity'] = os.environ.get('DEVELOPER_ID_APPLICATION', config.get('signing_identity', ''))
    config['notary_profile'] = os.environ.get('NOTARY_KEYCHAIN_PROFILE', config.get('notary_profile', ''))
    return config

def sign(app):
    app = Path(app)
    config = configuration()
    production = config['signing_mode'] == 'developer-id'
    if config['signing_mode'] not in ('ad-hoc', 'developer-id'):
        raise ValueError('signing_mode must be ad-hoc or developer-id')
    identity = config['signing_identity'] if production else '-'
    if production and not identity.startswith('Developer ID Application:'):
        raise ValueError('Set DEVELOPER_ID_APPLICATION to your Developer ID Application certificate name')
    flags = ['--options', 'runtime', '--timestamp'] if production else ['--options', '0']
    def seal(path, entitlements=None, preserve=False):
        args = ['codesign', '--force', '--sign', identity, *flags]
        if preserve:
            args += ['--preserve-metadata=entitlements']
        if entitlements:
            args += ['--entitlements', str(entitlements)]
        subprocess.run([*args, str(path)], check=True)
    framework = app / 'Contents/Frameworks/Sparkle.framework'
    version = framework / 'Versions/B'
    for service in ['Installer.xpc', 'Downloader.xpc']:
        path = version / 'XPCServices' / service
        if path.exists():
            seal(path, preserve=service == 'Downloader.xpc')
    seal(version / 'Autoupdate')
    seal(version / 'Updater.app')
    seal(framework)
    for helper in (app / 'Contents/Helpers').iterdir():
        if helper.is_file():
            seal(helper)
    seal(app, ROOT / 'release/Device.entitlements')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)

if __name__ == '__main__':
    sign(sys.argv[1])
