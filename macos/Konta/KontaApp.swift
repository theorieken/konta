import SwiftUI
import KontaKit
import UserNotifications

@main
struct KontaApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @State private var store = AppStore()
    var body: some Scene {
        WindowGroup { RootView().environment(store).frame(minWidth: 860, minHeight: 620) }
            .defaultSize(width: 1220, height: 840)
            .commands {
                CommandGroup(after: .newItem) {
                    Button("Aktualisieren") { Task { do { try await store.refresh() } catch { store.handle(error) } } }.keyboardShortcut("r")
                }
            }
        Settings { NavigationStack { SettingsView().environment(store) }.frame(width: 650, height: 720) }
    }
}
@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    private let notifications = NotificationDelegate()
    func applicationDidFinishLaunching(_ notification: Notification) { UNUserNotificationCenter.current().delegate = notifications }
    func application(_ application: NSApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) { NativeNotifications.shared.didRegister(deviceToken) }
    func application(_ application: NSApplication, didReceiveRemoteNotification userInfo: [String: Any]) { NotificationCenter.default.post(name: NativeNotifications.refresh, object: nil) }
}
