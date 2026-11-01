# GitHub distribution and automatic updates

## Everyday release

```sh
make publish                       # next patch; first release is 0.1.0
make publish VERSION=0.2.0          # choose a version explicitly
make publish RELEASE_ARGS=--minor  # bump the minor version
```

`make release` is an alias. Commit your changes first. The command fetches tags, checks the repository is public, verifies the update-signing key, runs Go/Swift/Python checks, builds a universal Mac app, signs it, creates an Applications drag-and-drop DMG and app-only ZIP, generates and verifies the signed Sparkle feed, and packages the standalone CLI/server. It pushes the source commit and version tag atomically, uploads a **draft** release, downloads and verifies every asset, then publishes it as latest. A build or upload failure leaves the previous public feed in place.

For review without publishing:

```sh
make release-build VERSION=0.2.0
make publish VERSION=0.2.0 RELEASE_ARGS=--dry-run
```

Prepared assets and their SHA-256 receipt live in `dist/releases/0.2.0/`. Repeating the same version reuses the verified artifacts only when the source commit, public update key, signing mode and hashes match. Retry a failed publication with the same command and version; draft assets can be replaced, published releases cannot. If a local build failed before its receipt was written, move that version's incomplete local output directory aside before retrying. Use a new higher version for corrections to published releases. Do not delete release tags to reuse version numbers.

## One-time setup on the release Mac

Requirements: macOS with Xcode 26+ and its command-line tools, Go 1.26.2+, Python 3.12+, GitHub CLI, and access to the public repository.

```sh
gh auth login
make release-setup
# Commit the public update key written to release/config.json.
git add release/config.json
git commit -m "Configure update signing"
make release-doctor
```

Sparkle 2.10.1 is downloaded from its official release and checked against a pinned SHA-256. The update private key is created in your login Keychain under account `dev.okestra.device`; only the public key is written to source. Keychain may ask you to allow the signing tool to use that key. Never put a private key in git, release assets or the app. Back up the Keychain key securely; losing it prevents existing ad-hoc installations from trusting future updates. The `generate_keys` tool supports private export/import for a deliberate secure backup or migration; those files must stay outside the repository.

`release/config.json` contains the repository, signing mode, Keychain account and public update key. Machine-specific certificate and notarization settings can go in ignored `.release/local.json`, or the environment. These settings are never bundled into the app.

## Without an Apple Developer account

The configured `ad-hoc` mode works without a paid Apple account. Every update archive and feed is cryptographically signed using Sparkle's Ed25519 key. The app bundle also receives a local integrity signature. **It is not Apple-notarized or Developer ID signed.**

Users download the DMG from GitHub Releases, drag the app into Applications, and launch it. If macOS blocks the first launch, the user must approve it in **System Settings → Privacy & Security → Open Anyway** and confirm the system prompt. This cannot be eliminated through code without Apple distribution credentials. No script disables Gatekeeper or removes quarantine.

## In-app updates

Published builds check the stable feed automatically, normally once daily. Users can also choose **Okestra Device → Check for Updates…**. **Settings → Updates** controls automatic checking and optional automatic download/install. Installation replaces the entire app bundle, including its matching CLI helper, icons, capture tools and update framework, then relaunches it. Existing device preferences and user files remain outside the bundle.

The feed is `https://github.com/jonace-mpelule/okestra-device/releases/latest/download/appcast.xml`. Each feed entry points to a version-specific immutable ZIP. Both the feed and archive are signed; verification happens before extraction. A release uses the same increasing `X.Y.Z` value for `CFBundleVersion` and `CFBundleShortVersionString`. Unsigned/malformed releases are rejected. Dev builds (`make device` without a version) do not contact the production feed.

The first release must be installed manually. Older builds from before Sparkle was added cannot acquire this feature automatically. This is stable-channel distribution; prerelease channels and binary deltas are not enabled. Automatic updates depend on GitHub being reachable. Keep published releases available for existing users.

The app's existing termination flow preserves recording finalization and asks about unsaved screenshot/review work before quitting. CLI/server upgrades are separate: the release includes their existing archive names and checksums, while Mac app updates use Sparkle.

## Upgrade to Developer ID signing later

Once you join Apple's Developer Program, install a **Developer ID Application** certificate (an Apple Development certificate is insufficient), then store notarization credentials using Apple's `xcrun notarytool store-credentials` flow. Keep passwords/API keys in Keychain, not this repository.

Set `signing_mode` to `developer-id` in `release/config.json`, and set the following environment variables or equivalent ignored `.release/local.json` fields:

```sh
export DEVELOPER_ID_APPLICATION='Developer ID Application: YOUR NAME (TEAMID)'
export NOTARY_KEYCHAIN_PROFILE='okestra-device-notary'
```

The local JSON keys are `signing_identity` and `notary_profile`. `make release-doctor` checks setup. The same publishing command then signs nested Sparkle services and helpers inside-out with Hardened Runtime, notarizes and staples the app, repackages it, creates and notarizes the DMG, and verifies acceptance before uploading. Keep the existing Sparkle key to allow installed ad-hoc versions to migrate to this signed release.

## Verification and recovery

- `make release-doctor` checks required tools, public GitHub access and local signing configuration.
- `make publish RELEASE_ARGS=--dry-run` makes no release, pushes no commits and changes no tags.
- `make release-build VERSION=X.Y.Z` creates reviewable artifacts without publishing.
- `python3 -m unittest discover -s scripts -p 'test_*.py'` covers release versioning, feed URL/signature metadata, key validation and build metadata alongside installer/network tests.
- If a new release has a defect, publish a higher fixed version. Existing installations never downgrade automatically.

References: [Sparkle setup and signing](https://sparkle-project.org/documentation/), [publishing updates](https://sparkle-project.org/documentation/publishing/), and [Apple notarization](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).
