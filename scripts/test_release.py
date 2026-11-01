import base64
import importlib.util
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent

def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

release = load('release')
configure = load('configure-app')

class ReleaseTests(unittest.TestCase):
    def test_next_version_orders_numeric_versions_and_bumps(self):
        tags = ['v0.9.9', 'v0.10.0', 'v0.2.0', 'experiment']
        self.assertEqual(release.next_version(tags), '0.10.1')
        self.assertEqual(release.next_version(tags, 'minor'), '0.11.0')
        self.assertEqual(release.next_version(tags, 'major'), '1.0.0')
        self.assertEqual(release.next_version([]), '0.1.0')

    def test_release_versions_cannot_be_development_or_prerelease_strings(self):
        for value in ['dev', '1.0', 'v1.0.0', '01.2.3', '1.2.3-beta', '../1.2.3']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.version_tuple(value)

    def test_update_key_must_be_a_base64_ed25519_public_key(self):
        self.assertTrue(release.public_key_valid(base64.b64encode(bytes(32)).decode()))
        for value in ['', 'bad!', None, base64.b64encode(bytes(31)).decode()]:
            self.assertFalse(release.public_key_valid(value))

    def test_feed_rejects_wrong_release_urls_sizes_versions_and_missing_signatures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'Okestra-Device-1.2.3.zip'
            archive.write_bytes(b'archive')
            def feed(version='1.2.3', url=None, size=7, signature='signed'):
                url = url or f'https://github.com/owner/app/releases/download/v1.2.3/{archive.name}'
                path = root / 'appcast.xml'
                path.write_text(f'<rss xmlns:sparkle="{release.SPARKLE_NS}"><channel><item>'
                                f'<sparkle:version>{version}</sparkle:version>'
                                f'<enclosure url="{url}" length="{size}" sparkle:edSignature="{signature}"/>'
                                '</item></channel></rss>')
                return path
            release.validate_feed(feed(), '1.2.3', archive, 'owner/app')
            for args in [{'url':'https://example.com/other.zip'}, {'size':8}, {'signature':''}, {'version':'1.2.2'}]:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    release.validate_feed(feed(**args), '1.2.3', archive, 'owner/app')

    def configure_fixture(self, version, key):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / 'release').mkdir()
        app = root / 'Device.app/Contents'
        app.mkdir(parents=True)
        (app / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'dev.okestra.device'}))
        (root / 'release/config.json').write_text(json.dumps({'repository':'owner/app','public_ed_key':key}))
        with patch.object(configure, 'ROOT', root):
            configure.configure(app.parent, version)
        return plistlib.loads((app / 'Info.plist').read_bytes())

    def test_release_metadata_enables_signed_updates_and_increments_bundle_version(self):
        key = base64.b64encode(bytes(32)).decode()
        info = self.configure_fixture('1.2.3', key)
        self.assertEqual(info['CFBundleVersion'], '1.2.3')
        self.assertEqual(info['SUPublicEDKey'], key)
        self.assertEqual(info['SUFeedURL'], 'https://github.com/owner/app/releases/latest/download/appcast.xml')
        self.assertTrue(info['SURequireSignedFeed'])
        self.assertTrue(info['SUVerifyUpdateBeforeExtraction'])
        self.assertFalse(info['SUSendProfileInfo'])
        self.assertFalse(info['SUAutomaticallyUpdate'])

    def test_development_builds_do_not_contact_the_production_update_feed(self):
        info = self.configure_fixture('dev', base64.b64encode(bytes(32)).decode())
        self.assertEqual(info['CFBundleVersion'], '0')
        self.assertNotIn('SUFeedURL', info)

    def test_unconfigured_release_cannot_accidentally_enable_unsigned_updates(self):
        info = self.configure_fixture('1.2.3', '')
        self.assertNotIn('SUFeedURL', info)

    def test_repository_must_be_a_simple_github_owner_and_name(self):
        for value in ['https://github.com/owner/app', 'owner/app/extra', 'owner/app?key=x']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.repository({'repository':value})

if __name__ == '__main__':
    unittest.main()
