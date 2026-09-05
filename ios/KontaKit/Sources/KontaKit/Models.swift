import Foundation

public enum RecordKind: String, Codable, CaseIterable, Identifiable, Sendable {
    case account, category, transaction, contract, loan, job
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .account: "Konto"
        case .category: "Kategorie"
        case .transaction: "Transaktion"
        case .contract: "Vertrag"
        case .loan: "Kredit"
        case .job: "Einkommen"
        }
    }
    public var plural: String {
        switch self {
        case .account: "Konten"
        case .category: "Kategorien"
        case .transaction: "Transaktionen"
        case .contract: "Verträge"
        case .loan: "Kredite"
        case .job: "Einkommen"
        }
    }
    public var symbol: String {
        switch self {
        case .account: "building.columns"
        case .category: "square.grid.2x2"
        case .transaction: "arrow.left.arrow.right"
        case .contract: "repeat"
        case .loan: "creditcard"
        case .job: "briefcase"
        }
    }
    public var isRecurring: Bool { [.contract, .loan, .job].contains(self) }
}

public enum Recurrence: String, Codable, CaseIterable, Identifiable, Sendable {
    case once, weekly, biweekly, monthly, quarterly, semiannual, yearly
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .once: "Einmalig"
        case .weekly: "Wöchentlich"
        case .biweekly: "Alle zwei Wochen"
        case .monthly: "Monatlich"
        case .quarterly: "Vierteljährlich"
        case .semiannual: "Halbjährlich"
        case .yearly: "Jährlich"
        }
    }
    var months: Int? {
        switch self { case .monthly: 1; case .quarterly: 3; case .semiannual: 6; case .yearly: 12; default: nil }
    }
}

/// Money crosses the wire as signed integer cents. Floating point never enters a balance.
public struct FinanceRecord: Codable, Identifiable, Hashable, Sendable {
    public var id: String = UUID().uuidString.lowercased()
    public var kind: RecordKind
    public var version: Int = 0
    public var name: String = ""
    public var notes: String = ""
    public var tags: [String] = []
    public var amount: Int64 = 0
    public var date: String = Day.string(Date())
    public var accountID: String? = nil
    public var categoryID: String? = nil
    public var state: String = "reality"
    public var direction: String = "expense"
    public var recurrence: Recurrence = .monthly
    public var intervalCount: Int = 1
    public var dayOfMonth: Int = 1
    public var endDate: String? = nil
    public var active: Bool = true
    public var includeInNetWorth: Bool = true
    public var accountType: String = "checking"
    public var bank: String = ""
    public var iban: String = ""
    public var counterparty: String = ""
    public var principal: Int64 = 0
    public var interestBasisPoints: Int = 0
    public var cancellationDays: Int = 0
    public var keywords: [String] = []
    public var budget: Int64 = 0
    public var categorySource: String = "manual"
    public var confidence: Double? = nil
    public var needsReview: Bool = false
    public var matchedPlanKey: String? = nil
    public var importHash: String? = nil
    public var createdAt: String? = nil
    public var updatedAt: String? = nil
    public init(kind: RecordKind) {
        self.kind = kind
        self.dayOfMonth = Day.calendar.component(.day, from: Date())
        if kind == .job { self.direction = "income" }
    }
}

public struct Household: Codable, Identifiable, Hashable, Sendable {
    public var id: String
    public var name: String
    public var role: String
    public var savingsGoal: Int64
    public var goalDate: String?
    public var horizon: Int
    public var aiEnabled: Bool
    public var aiModel: String
    public var version: Int
}
public struct User: Codable, Sendable {
    public var id: String
    public var name: String
    public var email: String
    public var verified: Bool
}
public struct Session: Codable, Sendable { public var token: String; public var user: User }
public struct Member: Codable, Identifiable, Sendable {
    public var id: String; public var name: String; public var email: String; public var role: String
}
public struct Invitation: Codable, Identifiable, Sendable {
    public var id: String; public var householdID: String; public var householdName: String
    public var email: String; public var expiresAt: String; public var status: String
}
public struct InboxItem: Codable, Identifiable, Sendable {
    public var id: String; public var title: String; public var body: String
    public var householdID: String?; public var invitationID: String?; public var read: Bool
}
public struct Upload: Codable, Identifiable, Sendable {
    public var id: String; public var name: String; public var status: String
    public var imported: Int; public var duplicates: Int; public var createdAt: String
}
public struct Snapshot: Codable, Sendable {
    public var household: Household
    public var records: [FinanceRecord]
    public var members: [Member]
    public var uploads: [Upload]
    public var invitations: [Invitation]
}
public struct Bootstrap: Codable, Sendable {
    public var user: User; public var households: [Household]; public var invitations: [Invitation]
    public var notifications: [InboxItem]
}

public enum Day {
    public static var calendar: Calendar {
        var result = Calendar(identifier: .gregorian)
        result.timeZone = TimeZone(identifier: "Europe/Berlin")!
        return result
    }
    public static func date(_ value: String) -> Date {
        let parts = value.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3, let date = calendar.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2], hour: 12)) else {
            return calendar.date(from: DateComponents(year: 1970, month: 1, day: 1, hour: 12))!
        }
        return date
    }
    public static func string(_ value: Date) -> String {
        let p = calendar.dateComponents([.year, .month, .day], from: value)
        return String(format: "%04d-%02d-%02d", p.year!, p.month!, p.day!)
    }
    public static func monthStart(_ value: Date) -> Date { date(String(string(value).prefix(7)) + "-01") }
    public static func addingMonths(_ months: Int, to value: Date) -> Date {
        calendar.date(byAdding: .month, value: months, to: value)!
    }
    public static func label(_ value: String) -> String {
        date(value).formatted(.dateTime.day().month(.abbreviated).year().locale(Locale(identifier: "de_DE")))
    }
}

public enum Euro {
    public static func format(_ cents: Int64) -> String {
        (Decimal(cents) / 100).formatted(.currency(code: "EUR").locale(Locale(identifier: "de_DE")))
    }
    public static func input(_ cents: Int64) -> String {
        NSDecimalNumber(decimal: Decimal(cents) / 100).stringValue.replacingOccurrences(of: ".", with: ",")
    }
    public static func parse(_ text: String) -> Int64? {
        let raw = text.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "€", with: "").replacingOccurrences(of: " ", with: "")
        let normalized = raw.contains(",") ? raw.replacingOccurrences(of: ".", with: "").replacingOccurrences(of: ",", with: ".") : raw
        guard normalized.range(of: #"^-?\d+(\.\d{1,2})?$"#, options: .regularExpression) != nil,
              let value = Decimal(string: normalized, locale: Locale(identifier: "en_US_POSIX")), abs(value) <= 1_000_000_000 else { return nil }
        return NSDecimalNumber(decimal: value * 100).int64Value
    }
}
