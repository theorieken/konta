import Foundation

enum DemoData {
    static func snapshot() -> Snapshot {
        let month = Day.monthStart(Date())
        let household = Household(id: "demo", name: "Unser Zuhause", role: "owner", savingsGoal: 2500000,
                                  goalDate: Day.string(Day.addingMonths(12, to: month)), horizon: 24, aiEnabled: false, aiModel: "gpt-4.1-mini", version: 1)
        var checking = FinanceRecord(kind: .account)
        checking.name = "Gemeinschaftskonto"; checking.bank = "Alltag & Fixkosten"; checking.amount = 428650
        checking.date = Day.string(month)
        var savings = FinanceRecord(kind: .account)
        savings.name = "Unsere Rücklage"; savings.bank = "Für alles, was kommt"; savings.accountType = "savings"
        savings.amount = 1240000; savings.date = checking.date
        let names = ["Wohnen", "Lebensmittel", "Freizeit", "Gehalt", "Abos", "Mobilität", "Sonstiges"]
        let categories = names.map { name in var c = FinanceRecord(kind: .category); c.name = name; c.direction = name == "Gehalt" ? "income" : "expense"; return c }
        var records = [checking, savings] + categories
        for (name, kind, amount, day, category) in [("Gehalt Alex", RecordKind.job, Int64(325000), 28, 3), ("Gehalt Sam", .job, 248000, 28, 3), ("Miete Zuhause", .contract, 128000, 1, 0), ("Internet & Mobilfunk", .contract, 6990, 15, 4), ("Deutschlandticket", .contract, 12600, 3, 5)] {
            var r = FinanceRecord(kind: kind); r.name = name; r.amount = amount; r.dayOfMonth = day
            r.date = checking.date; r.accountID = checking.id; r.categoryID = categories[category].id
            records.append(r)
        }
        let todayDay = Day.calendar.component(.day, from: Date())
        for (name, amount, day, category) in [("REWE · Wocheneinkauf", Int64(-8642), max(1, todayDay - 1), 1), ("Café am Park", -1850, max(1, todayDay - 2), 2), ("Alnatura", -4237, max(1, todayDay - 3), 1), ("Bücher & Gedanken", -2490, max(1, todayDay - 4), 2)] {
            var r = FinanceRecord(kind: .transaction); r.name = name; r.amount = amount
            r.date = Day.string(Day.calendar.date(byAdding: .day, value: day - 1, to: month)!)
            r.accountID = checking.id; r.categoryID = categories[category].id; records.append(r)
        }
        return Snapshot(household: household, records: records, members: [], uploads: [], invitations: [])
    }
}
