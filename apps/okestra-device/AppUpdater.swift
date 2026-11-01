import AppKit
import Combine
import Sparkle
import SwiftUI

@MainActor
final class DeviceAppUpdater: ObservableObject {
  @Published private(set) var canCheckForUpdates = false
  @Published private(set) var automaticallyChecks = false
  @Published private(set) var automaticallyDownloads = false
  private let updaterController: SPUStandardUpdaterController?
  private var started = false
  var configured: Bool { updaterController != nil }

  init() {
    let feed = Bundle.main.object(forInfoDictionaryKey: "SUFeedURL") as? String ?? ""
    let key = Bundle.main.object(forInfoDictionaryKey: "SUPublicEDKey") as? String ?? ""
    guard URL(string: feed)?.scheme == "https", Data(base64Encoded: key)?.count == 32 else {
      updaterController = nil
      return
    }
    let controller = SPUStandardUpdaterController(
      startingUpdater: false, updaterDelegate: nil, userDriverDelegate: nil)
    updaterController = controller
    controller.updater.publisher(for: \.canCheckForUpdates).assign(to: &$canCheckForUpdates)
    controller.updater.publisher(for: \.automaticallyChecksForUpdates).assign(to: &$automaticallyChecks)
    controller.updater.publisher(for: \.automaticallyDownloadsUpdates).assign(to: &$automaticallyDownloads)
  }

  func start() {
    guard !started else { return }
    started = true
    updaterController?.startUpdater()
  }

  func check() {
    guard let updaterController else {
      let alert = NSAlert()
      alert.messageText = "Updates aren't configured for this build"
      alert.informativeText = "Install a published release of Okestra Device to receive automatic updates."
      alert.runModal()
      return
    }
    updaterController.checkForUpdates(nil)
  }

  func setAutomaticChecks(_ enabled: Bool) {
    updaterController?.updater.automaticallyChecksForUpdates = enabled
  }
  func setAutomaticDownloads(_ enabled: Bool) {
    updaterController?.updater.automaticallyDownloadsUpdates = enabled
  }
}

struct DeviceUpdateSettings: View {
  @ObservedObject var updater: DeviceAppUpdater
  var body: some View {
    Form {
      Text("Keep Okestra Device up to date").font(.headline)
      Toggle("Automatically check for updates", isOn: Binding(
        get: { updater.automaticallyChecks }, set: updater.setAutomaticChecks))
      Toggle("Automatically download and install updates", isOn: Binding(
        get: { updater.automaticallyDownloads }, set: updater.setAutomaticDownloads))
        .disabled(!updater.automaticallyChecks)
      Text("Updates are verified before installation. The app will relaunch when an update is installed.")
        .font(.callout).foregroundStyle(.secondary)
      Button("Check for Updates…", action: updater.check)
        .disabled(updater.configured && !updater.canCheckForUpdates)
      if !updater.configured {
        Text("Automatic updates are available in published builds.").foregroundStyle(.secondary)
      }
    }.disabled(!updater.configured).padding(24).frame(width: 430)
  }
}
