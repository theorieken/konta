import Foundation
import UserNotifications
import Observation
#if os(iOS)
import UIKit
#else
import AppKit
#endif

@MainActor @Observable public final class NativeNotifications {
    public static let shared = NativeNotifications()
    public var deviceToken: String?
    public var enabled = false
    public static let refresh = Notification.Name("KontaRefresh")
    public static let registered = Notification.Name("KontaDeviceRegistered")
    public func requestAuthorization() async throws {
        enabled = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound])
        if enabled { register() }
    }
    public func restore() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        enabled = settings.authorizationStatus == .authorized || settings.authorizationStatus == .provisional
        if enabled { register() }
    }
    private func register() {
        #if os(iOS)
        UIApplication.shared.registerForRemoteNotifications()
        #else
        NSApplication.shared.registerForRemoteNotifications()
        #endif
    }
    public func didRegister(_ token: Data) {
        deviceToken = token.map { String(format: "%02x", $0) }.joined()
        NotificationCenter.default.post(name: Self.registered, object: nil)
    }
    public func schedule(records: [FinanceRecord], household: String) async throws {
        guard enabled else { return }
        let center = UNUserNotificationCenter.current()
        let prefix = "contract-\(household)-"
        let pending = await center.pendingNotificationRequests()
        center.removePendingNotificationRequests(withIdentifiers: pending.filter { $0.identifier.hasPrefix(prefix) }.map(\.identifier))
        // Keep room below the system's pending-notification limit.
        let due = records.filter { $0.kind == .contract && $0.active && $0.endDate != nil && $0.cancellationDays > 0 }
        let remaining = max(0, 60 - pending.filter { !$0.identifier.hasPrefix(prefix) }.count)
        for record in due.prefix(remaining) {
            guard let end = record.endDate, let date = Day.calendar.date(byAdding: .day, value: -record.cancellationDays, to: Day.date(end)) else { continue }
            let content = UNMutableNotificationContent()
            content.title = "Kündigungsfrist"
            content.body = "Eine Vertragsfrist steht an. Öffne Konta für die Details."
            content.sound = .default
            content.userInfo = ["householdID": household]
            var components = Day.calendar.dateComponents([.year, .month, .day], from: date)
            components.hour = 9; components.timeZone = Day.calendar.timeZone
            guard let deliveryDate = Day.calendar.date(from: components), deliveryDate > Date() else { continue }
            try await center.add(UNNotificationRequest(identifier: prefix + record.id, content: content, trigger: UNCalendarNotificationTrigger(dateMatching: components, repeats: false)))
        }
    }
    public func clearReminders() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
        UNUserNotificationCenter.current().removeAllDeliveredNotifications()
    }
    public func unregister() {
        #if os(iOS)
        UIApplication.shared.unregisterForRemoteNotifications()
        #else
        NSApplication.shared.unregisterForRemoteNotifications()
        #endif
        deviceToken = nil
    }
}

public final class NotificationDelegate: NSObject, UNUserNotificationCenterDelegate, Sendable {
    public func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        await MainActor.run { NotificationCenter.default.post(name: NativeNotifications.refresh, object: nil) }
        return [.banner, .sound, .list]
    }
    public func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        let household = response.notification.request.content.userInfo["householdID"] as? String
        await MainActor.run { NotificationCenter.default.post(name: NativeNotifications.refresh, object: household) }
    }
}
