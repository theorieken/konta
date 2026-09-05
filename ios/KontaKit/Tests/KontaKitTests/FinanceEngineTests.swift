import Testing
import Foundation
@testable import KontaKit

struct FinanceEngineTests {
    let today = Day.date("2026-09-05")
    func account() -> FinanceRecord {
        var result = FinanceRecord(kind: .account); result.name = "Girokonto"; result.amount = 100000; result.date = "2026-09-01"; return result
    }
    func transaction(_ account: FinanceRecord, amount: Int64, date: String, state: String = "reality") -> FinanceRecord {
        var result = FinanceRecord(kind: .transaction); result.accountID = account.id; result.amount = amount; result.date = date; result.state = state; return result
    }
    @Test func centsAreExact() {
        #expect(Euro.parse("1.234,56") == 123456)
        #expect(Euro.parse("-1234.56") == -123456)
        #expect(Euro.parse("0,01") == 1)
        #expect(Euro.parse("1,001") == nil)
        #expect(Euro.parse("NaN") == nil)
    }
    @Test func balanceTodayExcludesFutureAndPlansAndOldBookings() {
        let a = account()
        let records = [a, transaction(a, amount: -12345, date: "2026-09-03"), transaction(a, amount: 90000, date: "2026-09-30"), transaction(a, amount: -10000, date: "2026-09-04", state: "planned"), transaction(a, amount: 99999, date: "2026-08-31")]
        #expect(FinanceEngine.balance(records: records, at: today, includePlanned: false, today: today) == 87655)
        #expect(FinanceEngine.balance(records: records, at: today, includePlanned: true, today: today) == 77655)
    }
    @Test func accountFilterAndNetWorthExclusion() {
        let a = account(); var b = account(); b.amount = 75000; b.includeInNetWorth = false
        #expect(FinanceEngine.balance(records: [a, b], at: today, includePlanned: false, accountID: a.id) == 100000)
        #expect(FinanceEngine.balance(records: [a, b], at: today, includePlanned: false) == 100000)
        #expect(FinanceEngine.balance(records: [a, b], at: today, includePlanned: false, accountID: b.id) == 75000)
    }
    @Test func monthEndsDoNotDriftAfterFebruary() {
        var r = FinanceRecord(kind: .contract); r.date = "2026-01-01"; r.dayOfMonth = 31
        #expect(FinanceEngine.occurrences(r, through: Day.date("2026-04-30")) == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"])
        r.date = "2024-01-01"
        #expect(FinanceEngine.occurrences(r, through: Day.date("2024-02-29")).last == "2024-02-29")
    }
    @Test func intervalKeepsItsAnchorAndEnd() {
        var r = FinanceRecord(kind: .contract); r.date = "2026-01-20"; r.dayOfMonth = 15; r.recurrence = .quarterly; r.endDate = "2026-08-01"
        #expect(FinanceEngine.occurrences(r, through: Day.date("2027-01-01")) == ["2026-04-15", "2026-07-15"])
        r.recurrence = .weekly; r.intervalCount = 2; r.endDate = "2026-02-10"
        #expect(FinanceEngine.occurrences(r, through: Day.date("2027-01-01")) == ["2026-01-20", "2026-02-03"])
    }
    @Test func matchingKeepsOneMoneyMovement() {
        let a = account(); var source = FinanceRecord(kind: .contract)
        source.accountID = a.id; source.name = "Miete"; source.date = "2026-09-01"; source.dayOfMonth = 1; source.amount = 50000
        var paid = transaction(a, amount: -50000, date: "2026-09-02")
        paid.matchedPlanKey = "contract:\(source.id):2026-09-01"
        let records = [a, source, paid]
        #expect(FinanceEngine.movements(records, through: Day.date("2026-09-30"), today: today).count == 1)
        #expect(FinanceEngine.balance(records: records, at: today, includePlanned: true, today: today) == 50000)
        #expect(FinanceEngine.movements(records, through: Day.date("2026-10-31"), today: today).count == 2)
    }
    @Test func matchedOneOffIsExcluded() {
        let a = account(); let plan = transaction(a, amount: -20000, date: "2026-09-03", state: "planned")
        var paid = transaction(a, amount: -20100, date: "2026-09-04"); paid.matchedPlanKey = "transaction:\(plan.id):2026-09-03"
        #expect(FinanceEngine.balance(records: [a, plan, paid], at: today, includePlanned: true, today: today) == 79900)
    }
    @Test func loanFinalInstalmentIsCapped() {
        let a = account(); var loan = FinanceRecord(kind: .loan)
        loan.accountID = a.id; loan.date = "2026-09-01"; loan.dayOfMonth = 1; loan.principal = 25000; loan.amount = 10000
        let flows = FinanceEngine.movements([a, loan], through: Day.date("2027-09-30"), today: today)
        #expect(flows.map(\.amount) == [-10000, -10000, -5000])
    }
    @Test func loanInterestUsesDecimalRounding() {
        let a = account(); var loan = FinanceRecord(kind: .loan)
        loan.accountID = a.id; loan.date = "2026-09-01"; loan.dayOfMonth = 1; loan.principal = 100000; loan.amount = 60000; loan.interestBasisPoints = 1200
        #expect(FinanceEngine.movements([a, loan], through: Day.date("2027-09-30"), today: today).map(\.amount) == [-60000, -41410])
    }
    @Test func projectionIsDeterministicAndCountsSignedFlows() {
        let a = account(); let income = transaction(a, amount: 300000, date: "2026-09-28")
        let expense = transaction(a, amount: -128000, date: "2026-09-01")
        let points = FinanceEngine.projection(records: [a, income, expense], from: today, months: 2, today: today)
        #expect(points[0].balance == 272000); #expect(points[0].income == 300000); #expect(points[0].expense == -128000)
        #expect(points[1].balance == 272000)
    }
    @Test func invalidServerAddressesAreRejected() throws {
        #expect(throws: APIError.self) { try APIClient.validatedURL("https://user:secret@example.com") }
        #expect(throws: APIError.self) { try APIClient.validatedURL("http://bank.example.com") }
        #expect(try APIClient.validatedURL("https://api.example.com").host == "api.example.com")
    }
    @Test func realHTTPResponseDecodesWithoutAdapters() throws {
        let url = Bundle.module.url(forResource: "snapshot", withExtension: "json", subdirectory: "Fixtures")!
        let snapshot = try JSONDecoder().decode(Snapshot.self, from: Data(contentsOf: url))
        #expect(snapshot.records.filter { $0.kind == .category }.count == 23)
        #expect(snapshot.records.filter { $0.kind == .transaction }.reduce(Int64(0)) { $0 + $1.amount } == -135801)
        #expect(FinanceEngine.balance(records: snapshot.records, at: today, includePlanned: false, today: today) == -12345)
        #expect(snapshot.members.count == 2)
    }
}
