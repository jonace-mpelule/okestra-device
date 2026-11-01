# App icon

The app icon uses an original three-layer stacks vector mark matching the shape beside the app name. The editable source is `apps/okestra-device/AppIcon.icon`: each plate is a separate SVG/glass group, with light, dark and monochrome fill specializations. Shared square artwork supports Apple's iPhone/iPad/Mac icon canvas; this repository builds the macOS app.

`make device` invokes `scripts/build-icon.sh` before signing. Xcode 26 or later asset tools are required. The compiler creates `Assets.car` for modern Liquid Glass, dark, clear and tinted appearances, plus `AppIcon.icns` for macOS 13–15. The app's Info.plist declares both `CFBundleIconName` and `CFBundleIconFile`. The operating system selects the icon appearance; no app preference or runtime icon override is needed.

To rebuild only the icon resources:

```sh
./scripts/build-icon.sh
codesign --force --deep --sign - 'dist/Okestra Device.app'
```

Quit and reopen the app after rebuilding. Finder and Dock can cache icons for an unchanged bundle path.

Apple references: [Icon Composer](https://developer.apple.com/icon-composer/) and [creating your app icon](https://developer.apple.com/documentation/xcode/creating-your-app-icon-using-icon-composer).
