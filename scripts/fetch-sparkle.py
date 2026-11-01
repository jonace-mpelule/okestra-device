#!/usr/bin/env python3
"""Fetch the pinned official Sparkle SDK and verify its SHA-256 before extraction."""
import hashlib
from pathlib import Path
import subprocess
import tarfile
import tempfile
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
VERSION = '2.10.1'
SHA256 = '1a856d2a9edb8e628de88121d7be04cf0e2167f8641650b78fca00b14244cf27'
DEST = ROOT / '.cache' / 'sparkle' / VERSION

def fetch():
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 or newer is required for safe SDK extraction")
    if (DEST / '.verified').is_file() and (DEST / 'Sparkle.framework').is_dir():
        return DEST
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DEST.parent) as temporary:
        work = Path(temporary)
        archive = work / 'sdk.tar.xz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--proto', '=https',
                        '--proto-redir', '=https', f'https://github.com/sparkle-project/Sparkle/releases/download/{VERSION}/Sparkle-{VERSION}.tar.xz',
                        '--output', str(archive)], check=True)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError('Sparkle SDK checksum mismatch')
        extracted = work / 'sdk'
        extracted.mkdir()
        with tarfile.open(archive) as bundle:
            bundle.extractall(extracted, filter='data')
        if not (extracted / 'Sparkle.framework').is_dir():
            raise RuntimeError('Sparkle SDK is incomplete')
        (extracted / '.verified').write_text(SHA256 + '\n')
        if DEST.exists():
            shutil.rmtree(DEST)
        extracted.rename(DEST)
    return DEST

if __name__ == '__main__':
    print(fetch())
