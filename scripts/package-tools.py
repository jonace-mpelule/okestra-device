#!/usr/bin/env python3
"""Package standalone CLI/server tools, without embedding a second app updater."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent

def package(version, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for role in ['okestra-device', 'okestra-device-service']:
        for platform in (['darwin', 'linux'] if role == 'okestra-device' else ['linux']):
            for arch in ['amd64', 'arm64']:
                with tempfile.TemporaryDirectory() as temporary:
                    stage = Path(temporary)
                    env = dict(os.environ, GOOS=platform, GOARCH=arch)
                    subprocess.run(['go', 'build', '-trimpath', '-ldflags', os.environ.get('LDFLAGS', ''),
                                    '-o', str(stage / role), './cmd/' + role], cwd=ROOT, env=env, check=True)
                    scripts = ['install-cli.sh'] if role == 'okestra-device' else ['install-service.sh', 'setup-android-server.sh', 'android-tools.py', 'install-android.sh']
                    for name in scripts:
                        shutil.copy2(ROOT / 'scripts' / name, stage / name)
                    if platform == 'darwin':
                        shutil.copy2(ROOT / 'scripts/setup-android-mac.sh', stage / 'setup-android-mac.sh')
                    if role.endswith('-service'):
                        shutil.copy2(ROOT / 'deploy/systemd/okestra-device-service.service', stage / 'okestra-device-service.service')
                    with tarfile.open(destination / f'{role}_{version}_{platform}_{arch}.tar.gz', 'w:gz') as archive:
                        for child in sorted(stage.iterdir()):
                            archive.add(child, arcname=child.name)

if __name__ == '__main__':
    package(sys.argv[1], sys.argv[2])
