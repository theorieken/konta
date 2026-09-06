import SwiftUI
import Charts

struct DashboardView: View {
    @Environment(AppStore.self) private var store
    @State private var selected: FinanceRecord?
    private var points: [ProjectionPoint] { FinanceEngine.projection(records: store.records, from: store.rangeStart, months: store.rangeMonths) }
    private var balance: Int64 { FinanceEngine.balance(records: store.records, at: Date(), includePlanned: false) }
    private var end: Date { Day.calendar.date(byAdding: .day, value: -1, to: Day.addingMonths(store.rangeMonths, to: Day.monthStart(store.rangeStart)))! }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 26) {
                welcome
                range
                #if os(iOS)
                VStack(spacing: 12) {
                    metric("Vermögen heute", value: balance, symbol: "wallet.bifold", caption: "Gebuchte Umsätze bis heute")
                    HStack(alignment: .top, spacing: 16) {
                        compactMetric("Prognose", value: points.last?.balance ?? balance)
                        compactMetric("Spielraum / Monat", value: points.isEmpty ? 0 : points.reduce(0) { $0 + $1.income + $1.expense } / Int64(points.count))
                    }.padding(.horizontal, 4)
                }
                #else
                ViewThatFits(in: .horizontal) {
                    HStack(spacing: 16) { statCards }
                    VStack(spacing: 16) { statCards }
                }
                #endif
                projection
                ViewThatFits(in: .horizontal) {
                    HStack(alignment: .top, spacing: 20) { accounts.frame(minWidth: 280); goal.frame(minWidth: 280) }
                    VStack(spacing: 20) { accounts; goal }
                }
                categories
            }.padding(24).frame(maxWidth: 1200).frame(maxWidth: .infinity)
        }.background(KontaStyle.canvas)
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .refreshable { do { try await store.refresh() } catch { store.handle(error) } }
            .sheet(item: $selected) { record in NavigationStack { RecordDetailView(record: record) }.frame(idealWidth: 560, idealHeight: 620) }
    }
    private var welcome: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(store.household?.name.uppercased() ?? "DEIN ÜBERBLICK").font(.caption.weight(.semibold)).tracking(2).foregroundStyle(KontaStyle.accent)
            Text("Platz für eure Zukunft.").font(.system(.title, design: .rounded, weight: .bold))
            Text("Was heute da ist. Und was morgen möglich wird.").foregroundStyle(.secondary)
        }.padding(.vertical, 8)
    }
    private func compactMetric(_ title: String, value: Int64) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Money(cents: value).font(.system(.title3, design: .rounded, weight: .semibold)).lineLimit(1).minimumScaleFactor(0.7)
        }.frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 6)
    }
    private var range: some View {
        @Bindable var store = store
        return ViewThatFits(in: .horizontal) {
            HStack { DatePicker("Ab", selection: $store.rangeStart, displayedComponents: .date).fixedSize(); Spacer(); horizon }
            VStack(alignment: .leading) { DatePicker("Ab", selection: $store.rangeStart, displayedComponents: .date); horizon }
        }
    }
    private var horizon: some View {
        @Bindable var store = store
        return Picker("Zeitraum", selection: $store.rangeMonths) {
            Text("6 Monate").tag(6); Text("1 Jahr").tag(12); Text("2 Jahre").tag(24)
            if let horizon = store.household?.horizon, ![6, 12, 24].contains(horizon) { Text("\(horizon) Monate").tag(horizon) }
        }.pickerStyle(.segmented).frame(maxWidth: 310)
    }
    @ViewBuilder private var statCards: some View {
        metric("Vermögen heute", value: balance, symbol: "wallet.bifold", caption: "Gebuchte Umsätze bis heute")
        metric("Am Ende des Zeitraums", value: points.last?.balance ?? balance, symbol: "chart.line.uptrend.xyaxis", caption: "Inklusive geplanter Zahlungen")
        metric("Monatlicher Spielraum", value: points.isEmpty ? 0 : points.reduce(0) { $0 + $1.income + $1.expense } / Int64(points.count), symbol: "sparkles", caption: "Durchschnitt im gewählten Zeitraum")
    }
    private func metric(_ label: String, value: Int64, symbol: String, caption: String) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack { Text(label).font(.subheadline).foregroundStyle(.secondary); Spacer(); Image(systemName: symbol).foregroundStyle(KontaStyle.accent) }
            Money(cents: value).font(.system(.title, design: .rounded, weight: .semibold)).minimumScaleFactor(0.6).lineLimit(1)
            Text(caption).font(.caption).foregroundStyle(.secondary)
        }.padding(20).frame(minWidth: 200, maxWidth: .infinity, alignment: .leading)
            .kontaCard()
    }
    private var projection: some View {
        Panel(title: "So entwickelt sich euer Vermögen") {
            Chart {
                ForEach(points) { point in
                    AreaMark(x: .value("Monat", Day.date(point.date)), y: .value("Vermögen", Double(point.balance) / 100))
                        .foregroundStyle(LinearGradient(colors: [KontaStyle.accent.opacity(0.20), KontaStyle.accent.opacity(0.015)], startPoint: .top, endPoint: .bottom))
                    LineMark(x: .value("Monat", Day.date(point.date)), y: .value("Vermögen", Double(point.balance) / 100))
                        .foregroundStyle(KontaStyle.accent).lineStyle(StrokeStyle(lineWidth: 3))
                }
                if Date() >= Day.monthStart(store.rangeStart), Date() <= end {
                    RuleMark(x: .value("Heute", Date())).foregroundStyle(.secondary).lineStyle(StrokeStyle(lineWidth: 1, dash: [4]))
                        .annotation(position: .top, alignment: .leading) { Text("Heute").font(.caption2).foregroundStyle(.secondary) }
                }
                if let goal = store.household?.savingsGoal, goal > 0 {
                    RuleMark(y: .value("Sparziel", Double(goal) / 100)).foregroundStyle(KontaStyle.accent.opacity(0.5)).lineStyle(StrokeStyle(lineWidth: 1, dash: [5]))
                }
            }.frame(height: 255)
                .chartXAxis { AxisMarks(values: .stride(by: .month, count: max(1, store.rangeMonths / 6))) { AxisValueLabel(format: .dateTime.month(.abbreviated)); AxisGridLine() } }
                .chartYAxis { AxisMarks(position: .leading) { value in AxisGridLine(); AxisValueLabel { if let amount = value.as(Double.self) { Text((amount / 1000).formatted(.number.precision(.fractionLength(0)).locale(Locale(identifier: "de_DE"))) + " Tsd.") } } } }
                .accessibilityLabel("Vermögensprognose")
                .accessibilityValue("Am Ende des Zeitraums: \(Euro.format(points.last?.balance ?? balance))")
            HStack(spacing: 8) { Circle().fill(KontaStyle.accent).frame(width: 7, height: 7); Text("Prognose aus euren Buchungen und regelmäßigen Zahlungen").font(.caption).foregroundStyle(.secondary) }
        }
    }
    private var accounts: some View {
        Panel(title: "Eure Konten") {
            let records = store.records.filter { $0.kind == .account }
            if records.isEmpty { Text("Lege unter Konten dein erstes Konto an.").foregroundStyle(.secondary) }
            ForEach(records) { account in
                Button { selected = account } label: {
                    HStack(spacing: 12) {
                        Image(systemName: account.accountType == "savings" ? "leaf" : "building.columns").foregroundStyle(KontaStyle.accent).frame(width: 30)
                        VStack(alignment: .leading, spacing: 3) { Text(account.name).font(.subheadline.weight(.medium)); if !account.bank.isEmpty { Text(account.bank).font(.caption).foregroundStyle(.secondary) } }
                        Spacer()
                        Money(cents: FinanceEngine.balance(records: store.records, at: Date(), includePlanned: false, accountID: account.id)).font(.subheadline.weight(.medium))
                    }
                }.buttonStyle(.plain)
                if account.id != records.last?.id { Divider() }
            }
        }
    }
    private var goal: some View {
        Panel(title: "Ein Ziel, das näher rückt") {
            let target = store.household?.savingsGoal ?? 0
            if target > 0 {
                HStack(alignment: .firstTextBaseline) {
                    Money(cents: max(balance, 0)).font(.title2.weight(.semibold)); Text("von \(Euro.format(target))").font(.caption).foregroundStyle(.secondary)
                }
                ProgressView(value: min(max(Double(balance) / Double(target), 0), 1)).tint(KontaStyle.accent)
                if let date = store.household?.goalDate {
                    let projected = FinanceEngine.balance(records: store.records, at: Day.date(date), includePlanned: true)
                    Text(projected >= target ? "Euer Plan erreicht das Sparziel bis \(Day.label(date))." : "Bis \(Day.label(date)) fehlen laut Plan noch \(Euro.format(target - projected)).")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
            } else {
                Image(systemName: "scope").font(.largeTitle).foregroundStyle(KontaStyle.accent)
                Text("Was habt ihr vor?").font(.title3.weight(.semibold))
                Text("Legt unter Sparziele fest, was ihr erreichen möchtet. Konta zeigt, ob euer Plan dafür reicht.").font(.subheadline).foregroundStyle(.secondary)
            }
        }
    }
    private var categories: some View {
        Panel(title: "Wohin euer Geld fließt") {
            let flows = FinanceEngine.movements(store.records, through: end).filter { $0.amount < 0 && $0.date >= Day.string(Day.monthStart(store.rangeStart)) }
            let totals = Dictionary(grouping: flows, by: { $0.categoryID ?? "" }).mapValues { $0.reduce(Int64(0)) { $0 - $1.amount } }
            let sorted = store.records.filter { $0.kind == .category && (totals[$0.id] ?? 0) > 0 }.sorted { (totals[$0.id] ?? 0) > (totals[$1.id] ?? 0) }
            if sorted.isEmpty { Text("Deine Ausgaben erscheinen hier, sobald du Buchungen oder Verträge angelegt hast.").foregroundStyle(.secondary) }
            ForEach(sorted.prefix(6)) { category in
                VStack(spacing: 8) {
                    HStack { Text(category.name).font(.subheadline); Spacer(); Money(cents: -(totals[category.id] ?? 0), colored: true).font(.subheadline) }
                    ProgressView(value: Double(totals[category.id] ?? 0), total: Double(max(totals.values.max() ?? 1, 1))).tint(KontaStyle.accent.opacity(0.65))
                    if category.budget > 0 { Text("Monatsbudget: \(Euro.format(category.budget))").font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading) }
                }
            }
        }
    }
}
