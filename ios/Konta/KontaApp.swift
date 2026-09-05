import SwiftUI
import KontaKit
import UserNotifications

@main
struct KontaApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    private var store: AppStore { delegate.store }
    var body: some Scene {
        WindowGroup { RootView().environment(store) }
    }
}
@MainActor final class AppDelegate: NSObject, UIApplicationDelegate {
    let store = AppStore()
    private let notifications = NotificationDelegate()
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = notifications
        return true
    }
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) { NativeNotifications.shared.didRegister(deviceToken) }
    func application(_ application: UIApplication, didReceiveRemoteNotification userInfo: [AnyHashable: Any], fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
        Task {
            do {
                guard store.session != nil, !store.demo else { completionHandler(.noData); return }
                try await store.refresh()
                completionHandler(.newData)
            } catch { completionHandler(.failed) }
        }
    }
}
