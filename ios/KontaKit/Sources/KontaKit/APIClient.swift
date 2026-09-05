import Foundation
import Security
import CryptoKit

public struct APIError: LocalizedError, Sendable {
    public var status: Int
    public var message: String
    public var errorDescription: String? { message }
}
struct EmptyResponse: Decodable, Sendable { let ok: Bool }
private struct ErrorEnvelope: Decodable { var detail: String }

public struct APIClient: Sendable {
    public var baseURL: URL
    public var token: String?
    public init(baseURL: URL, token: String? = nil) { self.baseURL = baseURL; self.token = token }
    public static func validatedURL(_ value: String) throws -> URL {
        guard let url = URL(string: value.trimmingCharacters(in: .whitespacesAndNewlines)),
              let host = url.host, url.user == nil, url.password == nil, url.query == nil, url.fragment == nil else {
            throw APIError(status: 0, message: "Bitte eine gültige Server-Adresse eingeben.")
        }
        var allowed = url.scheme == "https"
        #if DEBUG
        allowed = allowed || (url.scheme == "http" && ["localhost", "127.0.0.1", "::1"].contains(host))
        #endif
        guard allowed else { throw APIError(status: 0, message: "Die Server-Adresse muss HTTPS verwenden.") }
        return url
    }
    public func request<T: Decodable & Sendable>(_ path: String, method: String = "GET", body: Data? = nil, contentType: String = "application/json") async throws -> T {
        let url = baseURL.appending(path: "v1/" + path)
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 90)
        request.httpMethod = method
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        if let token { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        let configuration = URLSessionConfiguration.ephemeral
        // Never forward a bearer credential to an HTTP redirect or a different origin.
        let session = URLSession(configuration: configuration, delegate: NoRedirect(), delegateQueue: nil)
        defer { session.finishTasksAndInvalidate() }
        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw APIError(status: 0, message: "Ungültige Server-Antwort.") }
        guard (200..<300).contains(response.statusCode) else {
            throw APIError(status: response.statusCode, message: (try? JSONDecoder().decode(ErrorEnvelope.self, from: data).detail) ?? "Server nicht erreichbar (\(response.statusCode)).")
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
    public func send<T: Decodable & Sendable, B: Encodable & Sendable>(_ path: String, method: String = "POST", body: B) async throws -> T {
        try await request(path, method: method, body: JSONEncoder().encode(body))
    }
    public func upload(household: String, account: String, url: URL) async throws -> Upload {
        let accessed = url.startAccessingSecurityScopedResource()
        defer { if accessed { url.stopAccessingSecurityScopedResource() } }
        let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
        guard size > 0, size <= 10 * 1024 * 1024 else { throw APIError(status: 0, message: "Bitte eine CSV-Datei bis 10 MB auswählen.") }
        let boundary = UUID().uuidString
        let safeName = url.lastPathComponent.replacingOccurrences(of: "\"", with: "").replacingOccurrences(of: "\r", with: "").replacingOccurrences(of: "\n", with: "")
        var body = Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"accountID\"\r\n\r\n\(account)\r\n--\(boundary)\r\nContent-Disposition: form-data; name=\"file\"; filename=\"\(safeName)\"\r\nContent-Type: text/csv\r\n\r\n".utf8)
        body.append(try Data(contentsOf: url))
        body.append(Data("\r\n--\(boundary)--\r\n".utf8))
        return try await request("households/\(household)/uploads", method: "POST", body: body, contentType: "multipart/form-data; boundary=\(boundary)")
    }
}
private final class NoRedirect: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) { completionHandler(nil) }
}

enum Vault {
    static func save(_ data: Data, key: String) throws {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "Konta", kSecAttrAccount as String: key]
        let update = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if update == errSecSuccess { return }
        guard update == errSecItemNotFound else { throw APIError(status: 0, message: "Schlüsselbund konnte nicht aktualisiert werden.") }
        var item = query
        item[kSecValueData as String] = data
        item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { throw APIError(status: 0, message: "Anmeldung konnte nicht sicher gespeichert werden.") }
    }
    static func read(_ key: String) -> Data? {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "Konta", kSecAttrAccount as String: key, kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess else { return nil }
        return result as? Data
    }
    static func delete(_ key: String) { SecItemDelete([kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "Konta", kSecAttrAccount as String: key] as CFDictionary) }
}

enum OfflineCache {
    private static var directory: URL { URL.applicationSupportDirectory.appending(path: "Konta/Snapshots") }
    private static func url(_ identity: String) -> URL { directory.appending(path: SHA256.hash(data: Data(identity.utf8)).map { String(format: "%02x", $0) }.joined()) }
    static func write(_ snapshot: Snapshot, identity: String, token: String) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let key = SymmetricKey(data: SHA256.hash(data: Data(token.utf8)))
        let bytes = try AES.GCM.seal(JSONEncoder().encode(snapshot), using: key).combined!
        try bytes.write(to: url(identity), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
    static func read(identity: String, token: String) -> Snapshot? {
        guard let data = try? Data(contentsOf: url(identity)), let box = try? AES.GCM.SealedBox(combined: data),
              let plain = try? AES.GCM.open(box, using: SymmetricKey(data: SHA256.hash(data: Data(token.utf8)))) else { return nil }
        return try? JSONDecoder().decode(Snapshot.self, from: plain)
    }
    static func clear() { try? FileManager.default.removeItem(at: directory) }
}
