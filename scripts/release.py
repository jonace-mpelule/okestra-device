#!/usr/bin/env python3
"""Build, sign and publish Okestra Device plus its signed Sparkle feed."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SPARKLE_NS = 'http://www.andymatuschak.org/xml-namespaces/sparkle'

def run(*args, capture=False, **kwargs):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, **kwargs)
    return result.stdout.strip() if capture else ''

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def config():
    return module('sign-app').configuration()

def version_tuple(version):
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise ValueError('Version must be X.Y.Z (for example 0.1.0)')
    return tuple(map(int, version.split('.')))

def next_version(tags, bump='patch'):
    versions = [version_tuple(t[1:]) for t in tags if re.fullmatch(r'v\d+\.\d+\.\d+', t)]
    if not versions:
        return '0.1.0'
    values = list(max(versions))
    index = {'major': 0, 'minor': 1, 'patch': 2}[bump]
    values[index] += 1
    for i in range(index + 1, 3):
        values[i] = 0
    return '.'.join(map(str, values))

def public_key_valid(key):
    try:
        return len(base64.b64decode(key, validate=True)) == 32
    except (ValueError, TypeError):
        return False

def repository(c):
    repo = c.get('repository', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Set repository to owner/name in release/config.json')
    return repo

def setup():
    sdk = module('fetch-sparkle').fetch()
    c = config()
    # Only the public key is read back or written to the repository.
    run(sdk / 'bin/generate_keys', '--account', c['keychain_account'])
    key = run(sdk / 'bin/generate_keys', '--account', c['keychain_account'], '-p', capture=True)
    if not public_key_valid(key):
        raise ValueError('Sparkle did not return a valid public key')
    path = ROOT / 'release/config.json'
    public = json.loads(path.read_text())
    if public.get('public_ed_key') and public['public_ed_key'] != key:
        raise ValueError('Existing public key differs. Restore the original signing key; do not silently rotate it.')
    public['public_ed_key'] = key
    path.write_text(json.dumps(public, indent=2) + '\n')
    print('Update signing is configured. Private key stays in your login Keychain. Commit release/config.json.')

def doctor(c, network=True):
    problems = []
    if sys.version_info < (3, 12):
        problems.append("Use Python 3.12 or newer")
    for command in ['git', 'go', 'swiftc', 'xcrun', 'codesign', 'ditto', 'hdiutil', 'gh', 'curl']:
        if not shutil.which(command):
            problems.append(f'Install {command}')
    if sys.platform != 'darwin':
        problems.append('Build the Mac release on macOS')
    repo = repository(c)
    if not public_key_valid(c.get('public_ed_key')):
        problems.append('Run make release-setup to create your update-signing key')
    else:
        sdk = module('fetch-sparkle').fetch()
        try:
            key = run(sdk / 'bin/generate_keys', '--account', c['keychain_account'], '-p', capture=True)
            if key != c['public_ed_key']:
                problems.append('The Keychain update key does not match release/config.json')
        except subprocess.CalledProcessError:
            problems.append('Restore the original Sparkle private key to your login Keychain')
    if c['signing_mode'] == 'developer-id':
        identity = c.get('signing_identity', '')
        identities = run('security', 'find-identity', '-v', '-p', 'codesigning', capture=True)
        if not identity.startswith('Developer ID Application:') or identity not in identities:
            problems.append('Install a Developer ID Application certificate and set DEVELOPER_ID_APPLICATION')
        if not c.get('notary_profile'):
            problems.append('Store notarytool credentials and set NOTARY_KEYCHAIN_PROFILE')
    elif c['signing_mode'] != 'ad-hoc':
        problems.append('signing_mode must be ad-hoc or developer-id')
    else:
        print('Distribution mode: ad-hoc + signed Sparkle updates. First launch requires macOS Open Anyway; this is not notarized.')
    if network:
        state = json.loads(run('gh', 'repo', 'view', repo, '--json', 'visibility', capture=True))
        if state['visibility'] != 'PUBLIC':
            problems.append(f'{repo} must be public for unauthenticated downloads and update checks')
        origin = run('git', 'remote', 'get-url', 'origin', capture=True)
        if origin not in [f'https://github.com/{repo}.git', f'https://github.com/{repo}', f'git@github.com:{repo}.git']:
            problems.append('origin must match release/config.json repository')
    if problems:
        raise ValueError('\n'.join(problems))
    print('Release requirements are ready.')

def validate_feed(path, version, archive, repo):
    tree = ET.parse(path)
    items = tree.findall('./channel/item')
    matching = [item for item in items if item.findtext(f'{{{SPARKLE_NS}}}version') == version]
    if len(matching) != 1:
        raise ValueError('Appcast must contain exactly one entry for this version')
    enclosure = matching[0].find('enclosure')
    expected = f'https://github.com/{repo}/releases/download/v{version}/{archive.name}'
    if enclosure is None or enclosure.get('url') != expected:
        raise ValueError('Appcast download URL does not match the release archive')
    signature = enclosure.get(f'{{{SPARKLE_NS}}}edSignature', '')
    if not signature or int(enclosure.get('length', '0')) != archive.stat().st_size:
        raise ValueError('Appcast is missing the signed archive or has an incorrect size')
    # Modern Sparkle can place version fields on the enclosure instead of the item;
    # generate_appcast currently emits item fields, validated above.

def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def manifest(c, version):
    return {'version': version, 'commit': run('git', 'rev-parse', 'HEAD', capture=True),
            'repository': repository(c), 'public_ed_key': c['public_ed_key'], 'signing_mode': c['signing_mode'],
            'signing_identity': c.get('signing_identity', '') if c['signing_mode'] == 'developer-id' else '-'}

def build(c, version):
    version_tuple(version)
    doctor(c)
    if run('git', 'status', '--porcelain', capture=True):
        raise ValueError('Commit your changes before building a release')
    output = ROOT / 'dist/releases' / version
    receipt = output / 'receipt.json'
    expected = manifest(c, version)
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if any(previous.get(k) != v for k, v in expected.items()):
            raise ValueError(f'{output} belongs to another build. Use a new version or move that local directory aside.')
        for name, digest in previous['assets'].items():
            if file_hash(output / name) != digest:
                raise ValueError(f'Prepared release asset changed: {name}')
        print(f'Reusing verified release artifacts in {output}')
        return output
    if output.exists() and any(output.iterdir()):
        raise ValueError(f'Incomplete build in {output}; move it aside before rebuilding this version')
    output.mkdir(parents=True, exist_ok=True)
    app = ROOT / '.release/build' / version / 'Okestra Device.app'
    run('go', 'vet', './...')
    run('go', 'test', '-race', './...')
    run('swift', 'test', '--package-path', 'apps/okestra-device', '--scratch-path', str(ROOT / '.cache/swift-tests'))
    run('python3', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py')
    env = dict(os.environ, OKESTRA_APP_OUTPUT=str(app))
    run('make', f'VERSION={version}', 'device', env=env)
    zip_path = output / f'Okestra-Device-{version}.zip'
    run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, zip_path)
    if c['signing_mode'] == 'developer-id':
        run('xcrun', 'notarytool', 'submit', zip_path, '--keychain-profile', c['notary_profile'], '--wait')
        run('xcrun', 'stapler', 'staple', app)
        run('xcrun', 'stapler', 'validate', app)
        zip_path.unlink()
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, zip_path)
        run('spctl', '--assess', '--type', 'execute', '--verbose=2', app)
    dmg_stage = ROOT / '.release/dmg' / version
    if dmg_stage.exists():
        shutil.rmtree(dmg_stage)
    dmg_stage.mkdir(parents=True)
    run('ditto', app, dmg_stage / app.name)
    (dmg_stage / 'Applications').symlink_to('/Applications')
    dmg = output / f'Okestra-Device-{version}.dmg'
    run('hdiutil', 'create', '-volname', 'Okestra Device', '-srcfolder', dmg_stage, '-ov', '-format', 'UDZO', dmg)
    if c['signing_mode'] == 'developer-id':
        run('codesign', '--sign', c['signing_identity'], '--timestamp', dmg)
        run('xcrun', 'notarytool', 'submit', dmg, '--keychain-profile', c['notary_profile'], '--wait')
        run('xcrun', 'stapler', 'staple', dmg)
        run('xcrun', 'stapler', 'validate', dmg)
    run('hdiutil', 'verify', dmg)
    sdk = module('fetch-sparkle').fetch()
    # Only the app-only ZIP goes into the feed, never the CLI/server archives or DMG.
    feed_stage = ROOT / '.release/feed' / version
    feed_stage.mkdir(parents=True, exist_ok=True)
    run('ditto', zip_path, feed_stage / zip_path.name)
    run(sdk / 'bin/generate_appcast', '--account', c['keychain_account'],
        '--download-url-prefix', f'https://github.com/{repository(c)}/releases/download/v{version}/',
        '--link', f'https://github.com/{repository(c)}/releases/tag/v{version}',
        '--maximum-deltas', '0', '-o', feed_stage / 'appcast.xml', feed_stage)
    shutil.copy2(feed_stage / 'appcast.xml', output / 'appcast.xml')
    validate_feed(output / 'appcast.xml', version, zip_path, repository(c))
    run(sdk / 'bin/sign_update', '--account', c['keychain_account'], '--verify', output / 'appcast.xml')
    # Keep CLI/server upgrade commands compatible with this same latest release.
    commit = run('git', 'rev-parse', '--short', 'HEAD', capture=True)
    ldflags = (f'-s -w -X github.com/jonace-mpelule/okestra-device/internal/version.Version={version} '
               f'-X github.com/jonace-mpelule/okestra-device/internal/version.Commit={commit}')
    run('python3', ROOT / 'scripts/package-tools.py', version, output,
        env=dict(os.environ, LDFLAGS=ldflags))
    assets = [zip_path, dmg, output / 'appcast.xml', *sorted(output.glob('*.tar.gz'))]
    sums = output / 'SHA256SUMS'
    sums.write_text(''.join(f'{file_hash(p)}  {p.name}\n' for p in assets))
    assets.append(sums)
    expected['assets'] = {p.name: file_hash(p) for p in assets}
    receipt.write_text(json.dumps(expected, indent=2) + '\n')
    print(f'Ready for review: {output}')
    return output

def publish(c, version):
    doctor(c)
    if run('git', 'status', '--porcelain', capture=True):
        raise ValueError('Commit your changes before publishing')
    repo = repository(c)
    tag = f'v{version}'
    head = run('git', 'rev-parse', 'HEAD', capture=True)
    # Never publish a stable version older than the latest public release.
    releases = json.loads(run('gh', 'api', f'repos/{repo}/releases?per_page=100', capture=True))
    stable = [r for r in releases if not r['draft'] and not r['prerelease']]
    versions = [version_tuple(r['tag_name'][1:]) for r in stable if re.fullmatch(r'v\d+\.\d+\.\d+', r['tag_name'])]
    if versions and version_tuple(version) <= max(versions):
        raise ValueError('Use a version newer than every published stable release')
    branch = run('git', 'symbolic-ref', '--short', 'HEAD', capture=True)
    remote = run('git', 'ls-remote', '--heads', 'origin', f'refs/heads/{branch}', capture=True).split()
    if remote:
        run('git', 'merge-base', '--is-ancestor', remote[0], head)
    tag_exists = tag in run('git', 'tag', '-l', capture=True).splitlines()
    if tag_exists and run('git', 'rev-list', '-n', '1', tag, capture=True) != head:
        raise ValueError('Release tag points to another commit')
    output = build(c, version)
    receipt = json.loads((output / 'receipt.json').read_text())
    if run('git', 'status', '--porcelain', capture=True) or run('git', 'rev-parse', 'HEAD', capture=True) != head:
        raise ValueError('Source changed during release preparation')
    if not tag_exists:
        run('git', 'tag', '-a', tag, '-m', f'Okestra Device {tag}')
    run('git', 'push', '--atomic', 'origin', f'HEAD:refs/heads/{branch}', f'refs/tags/{tag}')
    existing = [r for r in releases if r['tag_name'] == tag]
    if existing:
        if not existing[0]['draft']:
            raise ValueError('Release already published')
    else:
        notes = output / 'release-notes.md'
        notes.write_text(f'Okestra Device {version}\n\nDownload the DMG, drag Okestra Device to Applications, and open it.\n\n'
                         + ('This build is not notarized. On first launch, use macOS System Settings > Privacy & Security > Open Anyway if blocked.\n\n'
                            if c['signing_mode'] == 'ad-hoc' else '')
                         + 'Existing installations receive this version through Check for Updates.\n\n'
                         + f'Source commit: {head}. Supports Apple Silicon and Intel, macOS 13 or later.\n')
        run('gh', 'release', 'create', tag, '--repo', repo, '--verify-tag', '--draft',
            '--title', f'Okestra Device {version}', '--notes-file', notes)
    assets = [output / name for name in receipt['assets']]
    # Draft retry replaces only assets not yet visible to clients. Published releases are immutable.
    run('gh', 'release', 'upload', tag, *assets, '--repo', repo, '--clobber')
    downloaded = ROOT / '.release/verify' / version
    downloaded.mkdir(parents=True, exist_ok=True)
    run('gh', 'release', 'download', tag, '--repo', repo, '--dir', downloaded, '--clobber')
    for name, digest in receipt['assets'].items():
        if file_hash(downloaded / name) != digest:
            raise ValueError(f'GitHub upload verification failed for {name}; release remains a draft')
    run('gh', 'release', 'edit', tag, '--repo', repo, '--draft=false', '--latest')
    print(f'Published https://github.com/{repo}/releases/tag/{tag}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'doctor', 'build', 'publish'])
    parser.add_argument('--version', default='')
    parser.add_argument('--dry-run', action='store_true')
    bump = parser.add_mutually_exclusive_group()
    for option in ('patch', 'minor', 'major'):
        bump.add_argument('--' + option, action='store_true')
    args = parser.parse_args()
    c = config()
    if args.action == 'setup':
        setup(); return
    if args.action == 'doctor':
        doctor(c); return
    if not args.dry_run and args.action == 'publish':
        run('git', 'fetch', 'origin', '--tags')
    tags = run('git', 'tag', '-l', capture=True).splitlines()
    version = args.version or next_version(tags, 'major' if args.major else 'minor' if args.minor else 'patch')
    version_tuple(version)
    if args.dry_run:
        print(json.dumps({'action': args.action, 'version': version, 'repository': repository(c),
                          'signing_mode': c['signing_mode'], 'artifacts': ['universal DMG', 'app-only ZIP', 'signed appcast.xml', 'CLI/server archives', 'SHA256SUMS'],
                          'publish': 'Build and verify, push source/tag, upload a draft, verify downloads, publish as latest'}, indent=2))
        return
    if args.action == 'build':
        build(c, version)
    else:
        publish(c, version)

if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(f'release: {error}')
