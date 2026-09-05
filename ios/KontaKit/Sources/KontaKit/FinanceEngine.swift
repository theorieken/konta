import Foundation

public struct Movement: Identifiable, Sendable {
    public var id: String
    public var name: String
    public var amount: Int64
    public var date: String
    public var accountID: String
    public var categoryID: String?
    public var planned: Bool
    public var sourceID: String
    public var planKey: String?
}
public struct ProjectionPoint: Identifiable, Sendable {
    public var id: String { date }
    public var date: String
    public var balance: Int64
    public var income: Int64
    public var expense: Int64
}

/// Virtual plans belong to the native clients. Their stable keys retain the paid-plan audit link.
public enum FinanceEngine {
    public static func occurrences(_ source: FinanceRecord, through end: Date) -> [String] {
        guard source.active else { return [] }
        let start = Day.date(source.date)
        let until = min(end, source.endDate.map(Day.date) ?? end)
        guard start <= until else { return [] }
        if source.recurrence == .once { return [source.date] }
        let factor = max(1, source.intervalCount)
        var result: [String] = []
        // The API bounds dates and intervalCount; the guard also protects an offline snapshot.
        for index in 0..<20_000 {
            let due: Date
            if let months = source.recurrence.months {
                let month = Day.addingMonths(index * months * factor, to: Day.monthStart(start))
                let days = Day.calendar.range(of: .day, in: .month, for: month)!.count
                due = Day.calendar.date(byAdding: .day, value: min(max(1, source.dayOfMonth), days) - 1, to: month)!
            } else {
                due = Day.calendar.date(byAdding: .day, value: index * factor * (source.recurrence == .weekly ? 7 : 14), to: start)!
            }
            if due > until { break }
            if due >= start { result.append(Day.string(due)) }
        }
        return result
    }

    public static func movements(_ records: [FinanceRecord], through until: Date, today: Date = Date()) -> [Movement] {
        let bookings = records.filter { $0.kind == .transaction }
        let matched = Set(bookings.compactMap(\.matchedPlanKey))
        var result = bookings.filter { $0.date <= Day.string(until) }.compactMap { record -> Movement? in
            guard let account = record.accountID else { return nil }
            if record.state == "planned", matched.contains("transaction:\(record.id):\(record.date)") { return nil }
            return Movement(id: record.id, name: record.name, amount: record.amount, date: record.date,
                            accountID: account, categoryID: record.categoryID, planned: record.state == "planned",
                            sourceID: record.id, planKey: record.state == "planned" ? "transaction:\(record.id):\(record.date)" : nil)
        }
        let firstMonth = Day.string(Day.monthStart(today))
        for source in records where source.kind.isRecurring {
            guard let account = source.accountID else { continue }
            var outstanding = source.principal
            for due in occurrences(source, through: until) {
                var magnitude = abs(source.amount)
                if source.kind == .loan {
                    guard outstanding > 0 else { break }
                    // Interest accrues per instalment interval, rounded once to whole cents.
                    let annualPeriods: Decimal
                    switch source.recurrence {
                    case .weekly: annualPeriods = 52
                    case .biweekly: annualPeriods = 26
                    case .monthly: annualPeriods = 12
                    case .quarterly: annualPeriods = 4
                    case .semiannual: annualPeriods = 2
                    case .yearly, .once: annualPeriods = 1
                    }
                    var interest = Decimal(outstanding) * Decimal(source.interestBasisPoints) * Decimal(source.intervalCount) / 10_000 / annualPeriods
                    var rounded = Decimal()
                    NSDecimalRound(&rounded, &interest, 0, .plain)
                    let accrued = NSDecimalNumber(decimal: rounded).int64Value
                    magnitude = min(magnitude, outstanding + accrued)
                    outstanding = max(0, outstanding + accrued - magnitude)
                }
                let key = "\(source.kind.rawValue):\(source.id):\(due)"
                guard due >= firstMonth, !matched.contains(key) else { continue }
                let amount = source.kind == .job || (source.kind == .contract && source.direction == "income") ? magnitude : -magnitude
                result.append(Movement(id: key, name: source.name, amount: amount, date: due, accountID: account,
                                       categoryID: source.categoryID, planned: true, sourceID: source.id, planKey: key))
            }
        }
        return result.sorted { ($0.date, $0.id) < ($1.date, $1.id) }
    }

    public static func balance(records: [FinanceRecord], at day: Date, includePlanned: Bool, today: Date = Date(), accountID: String? = nil) -> Int64 {
        let date = Day.string(day)
        let accounts = records.filter { $0.kind == .account && (accountID == nil || $0.id == accountID) }
            .filter { accountID != nil || $0.includeInNetWorth }
        let eligible = Dictionary(uniqueKeysWithValues: accounts.filter { $0.date <= date }.map { ($0.id, $0) })
        let opening = eligible.values.reduce(Int64(0)) { $0 + $1.amount }
        return movements(records, through: day, today: today).reduce(opening) { total, movement in
            guard let account = eligible[movement.accountID], movement.date >= account.date,
                  includePlanned || !movement.planned else { return total }
            return total + movement.amount
        }
    }

    public static func projection(records: [FinanceRecord], from: Date, months: Int, today: Date = Date()) -> [ProjectionPoint] {
        let start = Day.monthStart(from)
        return (0..<min(max(months, 1), 120)).map { offset in
            let month = Day.addingMonths(offset, to: start)
            let next = Day.addingMonths(1, to: month)
            let end = Day.calendar.date(byAdding: .day, value: -1, to: next)!
            let fromDay = Day.string(month)
            let eligible = Set(records.filter { $0.kind == .account && $0.includeInNetWorth }.map(\.id))
            let flows = movements(records, through: end, today: today).filter { $0.date >= fromDay && eligible.contains($0.accountID) }
            return ProjectionPoint(date: Day.string(end), balance: balance(records: records, at: end, includePlanned: true, today: today),
                                   income: flows.filter { $0.amount > 0 }.reduce(0) { $0 + $1.amount },
                                   expense: flows.filter { $0.amount < 0 }.reduce(0) { $0 + $1.amount })
        }
    }
}
