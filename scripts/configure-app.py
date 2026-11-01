#!/usr/bin/env python3
"""Write version/update metadata without embedding local signing credentials."""
import base64
import json
from pathlib import Path
import plistlib
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

def configure(app, version):
    path = Path(app) / 'Contents/Info.plist'
    info = plistlib.loads(path.read_bytes())
    release = bool(re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version))
    info['CFBundleShortVersionString'] = version if release else '0.0.0'
    info['CFBundleVersion'] = version if release else '0'
    config = json.loads((ROOT / 'release/config.json').read_text())
    key = config.get('public_ed_key', '')
    if release and key:
        if len(base64.b64decode(key, validate=True)) != 32:
            raise ValueError('Invalid Sparkle public key')
        repo = config['repository']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Invalid GitHub repository')
        info.update(SUFeedURL=f'https://github.com/{repo}/releases/latest/download/appcast.xml',
                    SUPublicEDKey=key, SURequireSignedFeed=True, SUVerifyUpdateBeforeExtraction=True,
                    SUEnableAutomaticChecks=True, SUAutomaticallyUpdate=False,
                    SUScheduledCheckInterval=86400, SUSendProfileInfo=False)
    path.write_bytes(plistlib.dumps(info))

if __name__ == '__main__':
    configure(sys.argv[1], sys.argv[2])
