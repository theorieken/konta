import Foundation
import Observation

@MainActor @Observable public final class AppStore {
    public var server: String
    public var session: Session?
    public var households: [Household] = []
    public var invitations: [Invitation] = []
    public var notifications: [InboxItem] = []
    public var snapshot: Snapshot?
    public var selectedHouseholdID: String?
    public var error: String?
    public var message: String?
    public var busy = false
    public var offline = false
    public var demo = false
    public var rangeStart = Day.monthStart(Date())
    public var rangeMonths = 12
    private var refreshGeneration = 0
    public var records: [FinanceRecord] { snapshot?.records ?? [] }
    public var household: Household? { snapshot?.household }
    public var isOwner: Bool { household?.role == "owner" }
    public var canWrite: Bool { !offline && !demo && !busy }
    public init() {
        #if DEBUG
        let defaultServer = "http://localhost:8765"
        #else
        let defaultServer = Bundle.main.object(forInfoDictionaryKey: "KontaAPIURL") as? String ?? ""
        #endif
        server = UserDefaults.standard.string(forKey: "konta.server") ?? defaultServer
        if let data = Vault.read("session:" + server) { session = try? JSONDecoder().decode(Session.self, from: data) }
        selectedHouseholdID = UserDefaults.standard.string(forKey: "konta.household")
        if ProcessInfo.processInfo.arguments.contains("--demo") { startDemo() }
    }
    public func client() throws -> APIClient { APIClient(baseURL: try APIClient.validatedURL(server), token: session?.token) }
    public func perform(_ action: () async throws -> Void) async {
        guard !busy else { return }
        busy = true
        defer { busy = false }
        do { try await action() } catch { handle(error) }
    }
    public func handle(_ failure: Error) {
        if let api = failure as? APIError, api.status == 401 { clearSession() }
        error = failure.localizedDescription
    }
    public func login(name: String, email: String, password: String, register: Bool) async throws {
        struct Credentials: Encodable, Sendable { let name: String; let email: String; let password: String }
        let url = try APIClient.validatedURL(server)
        let result: Session = try await APIClient(baseURL: url).send("auth/" + (register ? "register" : "login"), body: Credentials(name: name, email: email, password: password))
        try Vault.save(JSONEncoder().encode(result), key: "session:" + server)
        UserDefaults.standard.set(server, forKey: "konta.server")
        session = result
        try await refresh()
        await NativeNotifications.shared.restore()
        await registerDevice()
    }
    public func refresh() async throws {
        guard session != nil, !demo else { return }
        refreshGeneration += 1
        let generation = refreshGeneration
        let api = try client()
        do {
            let bootstrap: Bootstrap = try await api.request("bootstrap")
            guard generation == refreshGeneration, session != nil else { return }
            session?.user = bootstrap.user
            households = bootstrap.households
            invitations = bootstrap.invitations
            notifications = bootstrap.notifications
            if !households.contains(where: { $0.id == selectedHouseholdID }) { selectedHouseholdID = households.first?.id; snapshot = nil }
            if let id = selectedHouseholdID {
                let result: Snapshot = try await api.request("households/\(id)/snapshot")
                guard generation == refreshGeneration, id == selectedHouseholdID else { return }
                snapshot = result
                if let session { try? OfflineCache.write(result, identity: server + session.user.id + id, token: session.token) }
                try? await NativeNotifications.shared.schedule(records: result.records, household: id)
                UserDefaults.standard.set(id, forKey: "konta.household")
            }
            offline = false
        } catch {
            guard generation == refreshGeneration else { return }
            if let apiError = error as? APIError, [401, 403, 404].contains(apiError.status) {
                snapshot = nil; OfflineCache.clear(); throw error
            }
            offline = true
            if snapshot == nil, let session, let id = selectedHouseholdID {
                snapshot = OfflineCache.read(identity: server + session.user.id + id, token: session.token)
            }
            throw error
        }
    }
    public func selectHousehold(_ id: String) async {
        guard id != selectedHouseholdID else { return }
        refreshGeneration += 1
        snapshot = nil
        selectedHouseholdID = id
        do { try await refresh() } catch { handle(error) }
    }
    public func save(_ record: FinanceRecord) async throws {
        guard let id = selectedHouseholdID, !demo, !offline else { throw APIError(status: 0, message: "Zum Speichern bitte mit einem Haushalt verbinden.") }
        let _: FinanceRecord = try await client().send("households/\(id)/records/\(record.kind.rawValue)/\(record.id)", method: "PUT", body: record)
        try await refresh()
    }
    public func delete(_ record: FinanceRecord) async throws {
        guard let id = selectedHouseholdID else { return }
        let _: EmptyResponse = try await client().send("households/\(id)/records/\(record.id)", method: "DELETE", body: ["version": record.version])
        try await refresh()
    }
    public func createHousehold(_ name: String) async throws {
        let result: Household = try await client().send("households", body: ["name": name])
        selectedHouseholdID = result.id; snapshot = nil
        try await refresh()
    }
    public func command<B: Encodable & Sendable>(_ path: String, method: String = "POST", body: B) async throws {
        let _: EmptyResponse = try await client().send(path, method: method, body: body)
        try await refresh()
    }
    public func invite(_ email: String) async throws {
        guard let id = selectedHouseholdID else { return }
        let _: Invitation = try await client().send("households/\(id)/invitations", body: ["email": email])
        try await refresh(); message = "Einladung wurde angelegt."
    }
    public func updateHousehold(_ household: Household) async throws {
        let _: Household = try await client().send("households/\(household.id)", method: "PATCH", body: household)
        try await refresh()
    }
    public func upload(_ url: URL, account: String) async throws {
        guard let id = selectedHouseholdID else { return }
        let result = try await client().upload(household: id, account: account, url: url)
        try await refresh()
        message = "\(result.imported) Buchungen importiert · \(result.duplicates) Duplikate übersprungen"
    }
    public func classify() async throws {
        guard let id = selectedHouseholdID else { return }
        let ids = records.filter { $0.kind == .transaction && $0.categorySource != "manual" && $0.matchedPlanKey == nil && $0.needsReview }.map(\.id)
        struct Result: Decodable, Sendable { let classified: Int }
        var count = 0
        for offset in stride(from: 0, to: ids.count, by: 25) {
            let result: Result = try await client().send("households/\(id)/classify", body: ["ids": Array(ids[offset..<min(offset + 25, ids.count)])])
            count += result.classified
        }
        try await refresh(); message = "\(count) Buchungen mit KI zugeordnet."
    }
    public func logout() async throws {
        // A failed server revocation must never keep private data on a signed-out device.
        defer { clearSession() }
        if !demo, session != nil {
            let _: EmptyResponse = try await client().send("auth/logout", body: ["deviceToken": NativeNotifications.shared.deviceToken ?? ""])
        }
    }
    public func clearSession() {
        refreshGeneration += 1
        Vault.delete("session:" + server); OfflineCache.clear()
        session = nil; snapshot = nil; households = []; invitations = []; notifications = []
        selectedHouseholdID = nil; demo = false; offline = false
        NativeNotifications.shared.clearReminders()
        NativeNotifications.shared.unregister()
    }
    public func registerDevice() async {
        guard !demo, session != nil, let token = NativeNotifications.shared.deviceToken else { return }
        #if os(iOS)
        let platform = "ios"
        #else
        let platform = "macos"
        #endif
        #if DEBUG
        let environment = "development"
        #else
        let environment = "production"
        #endif
        do {
            let _: EmptyResponse = try await client().send("devices", body: ["token": token, "platform": platform, "environment": environment])
        } catch { handle(error) }
    }
    public func startDemo() {
        demo = true; offline = false
        let sample = DemoData.snapshot()
        snapshot = sample; households = [sample.household]; selectedHouseholdID = sample.household.id
        session = Session(token: "demo", user: User(id: "demo", name: "Alex", email: "demo@example.com", verified: true))
    }
}
