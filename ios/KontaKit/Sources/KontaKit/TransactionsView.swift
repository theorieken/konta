import SwiftUI

struct PaymentsView: View {
    @Environment(AppStore.self) private var store
    @State private var query = ""
    @State private var direction = "all"
    @State private var status = "all"
    @State private var selected: FinanceRecord?
    @State private var creating: FinanceRecord?

    private var until: Date {
        Day.calendar.date(
            byAdding: .day,
            value: -1,
            to: Day.addingMonths(store.rangeMonths, to: Day.monthStart(store.rangeStart))
        )!
    }

    private var payments: [Movement] {
        FinanceEngine.movements(store.records, through: until)
            .filter { movement in
                store.records.first(where: { $0.id == movement.sourceID })?.kind == .transaction
                    && movement.date >= Day.string(Day.monthStart(store.rangeStart))
                    && (query.isEmpty || movement.name.localizedCaseInsensitiveContains(query))
                    && (direction == "all"
                        || (direction == "income" && movement.amount >= 0)
                        || (direction == "expense" && movement.amount < 0))
                    && matchesStatus(movement)
            }
            .sorted { ($0.date, $0.id) > ($1.date, $1.id) }
    }

    private var total: Int64 { payments.reduce(0) { $0 + $1.amount } }
    private var income: Int64 { payments.filter { $0.amount >= 0 }.reduce(0) { $0 + $1.amount } }
    private var expense: Int64 { payments.filter { $0.amount < 0 }.reduce(0) { $0 + $1.amount } }

    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 14) {
                Text(Day.label(Day.string(Day.monthStart(store.rangeStart))) + " – " + Day.label(Day.string(until)))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                ViewThatFits(in: .horizontal) {
                    HStack(spacing: 24) { summaries }
                    VStack(alignment: .leading, spacing: 10) { summaries }
                }

                HStack(spacing: 12) {
                    Picker("Richtung", selection: $direction) {
                        Text("Alle").tag("all")
                        Text("Eingänge").tag("income")
                        Text("Ausgänge").tag("expense")
                    }
                    Picker("Status", selection: $status) {
                        Text("Alle").tag("all")
                        Text("Gebucht").tag("booked")
                        Text("Geplant").tag("planned")
                        Text("Zu prüfen").tag("review")
                    }
                }
                .pickerStyle(.segmented)
            }
            .padding(20)
            .frame(maxWidth: 900, alignment: .leading)
            .frame(maxWidth: .infinity)

            List {
                if payments.isEmpty {
                    ContentUnavailableView(
                        "Noch keine Zahlungen",
                        systemImage: "arrow.left.arrow.right",
                        description: Text("Erfasse eine Zahlung oder importiere Umsätze in den Einstellungen.")
                    )
                }
                ForEach(payments) { movement in
                    Button {
                        selected = store.records.first { $0.id == movement.sourceID }
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: movement.amount >= 0 ? "arrow.down.left" : "arrow.up.right")
                                .foregroundStyle(movement.amount >= 0 ? KontaStyle.income : KontaStyle.expense)
                                .frame(width: 34, height: 34)
                                .background(
                                    (movement.amount >= 0 ? KontaStyle.income : KontaStyle.expense).opacity(0.08),
                                    in: Circle()
                                )
                            VStack(alignment: .leading, spacing: 4) {
                                Text(movement.name).font(.body.weight(.medium)).lineLimit(2)
                                Text(paymentSubtitle(movement))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer(minLength: 8)
                            Money(cents: movement.amount, colored: true)
                                .font(.body.weight(.semibold))
                        }
                        .padding(.vertical, 6)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
            .listStyle(.plain)
            .frame(maxWidth: 900)
            .frame(maxWidth: .infinity)
        }
        .searchable(text: $query, prompt: "Zahlungen suchen")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    Button("Eingang", systemImage: "arrow.down.left") { create(direction: "income") }
                    Button("Ausgang", systemImage: "arrow.up.right") { create(direction: "expense") }
                } label: {
                    Label("Neue Zahlung", systemImage: "plus")
                }
                .disabled(!store.canWrite)
            }
        }
        .sheet(item: $selected) { record in
            NavigationStack { RecordDetailView(record: record) }
                .frame(idealWidth: 560, idealHeight: 650)
        }
        .sheet(item: $creating) { record in
            NavigationStack { RecordEditor(record: record) }
                .frame(idealWidth: 580, idealHeight: 680)
        }
    }

    @ViewBuilder private var summaries: some View {
        summary("Eingänge", amount: income, color: KontaStyle.income)
        summary("Ausgänge", amount: expense, color: KontaStyle.expense)
        summary("Saldo", amount: total, color: .secondary)
    }

    private func summary(_ title: String, amount: Int64, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Money(cents: amount, colored: title != "Saldo")
                .font(.title3.weight(.semibold))
        }
        .frame(minWidth: 130, alignment: .leading)
        .accessibilityElement(children: .combine)
    }

    private func matchesStatus(_ movement: Movement) -> Bool {
        switch status {
        case "booked": return !movement.planned
        case "planned": return movement.planned
        case "review":
            return store.records.first(where: { $0.id == movement.sourceID })?.needsReview == true
        default: return true
        }
    }

    private func paymentSubtitle(_ movement: Movement) -> String {
        Day.label(movement.date) + (movement.planned
            ? (movement.date < Day.string(Date()) ? " · Überfällig" : " · Geplant")
            : " · Gebucht")
    }

    private func create(direction: String) {
        var record = FinanceRecord(kind: .transaction)
        record.direction = direction
        record.accountID = store.records.first { $0.kind == .account }?.id
        record.categoryID = store.records.first {
            $0.kind == .category && ($0.direction == direction || $0.direction == "both")
        }?.id
        creating = record
    }
}

struct RecurringCardsView: View {
    let kind: RecordKind
    @Environment(AppStore.self) private var store
    @State private var selected: FinanceRecord?
    @State private var creating: FinanceRecord?
    @State private var query = ""

    private var records: [FinanceRecord] {
        store.records
            .filter { $0.kind == kind && (query.isEmpty || $0.name.localizedCaseInsensitiveContains(query)) }
            .sorted { lhs, rhs in
                if lhs.active != rhs.active { return lhs.active }
                return lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
            }
    }

    var body: some View {
        ScrollView {
            if records.isEmpty {
                ContentUnavailableView {
                    Label(emptyTitle, systemImage: kind.symbol)
                } description: {
                    Text(emptyDescription)
                } actions: {
                    Button("Neu anlegen", systemImage: "plus") { create() }
                        .disabled(!store.canWrite)
                }
                .frame(maxWidth: .infinity, minHeight: 420)
            } else {
                LazyVGrid(
                    columns: [GridItem(.adaptive(minimum: 260, maximum: 380), spacing: 16)],
                    alignment: .leading,
                    spacing: 16
                ) {
                    ForEach(records) { record in
                        Button { selected = record } label: {
                            recurringCard(record)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(24)
                .frame(maxWidth: 1100)
                .frame(maxWidth: .infinity)
            }
        }
        .background(KontaStyle.canvas)
        .searchable(text: $query, prompt: "\(kind.plural) suchen")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { create() } label: { Label("Neu", systemImage: "plus") }
                    .disabled(!store.canWrite)
            }
        }
        .sheet(item: $selected) { record in
            NavigationStack { RecordDetailView(record: record) }
                .frame(idealWidth: 560, idealHeight: 650)
        }
        .sheet(item: $creating) { record in
            NavigationStack { RecordEditor(record: record) }
                .frame(idealWidth: 580, idealHeight: 680)
        }
    }

    private func recurringCard(_ record: FinanceRecord) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Image(systemName: kind.symbol)
                    .font(.title3)
                    .foregroundStyle(KontaStyle.accent)
                    .frame(width: 42, height: 42)
                    .background(KontaStyle.accent.opacity(0.09), in: RoundedRectangle(cornerRadius: 13))
                Spacer()
                if !record.active {
                    Text("Pausiert")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                }
            }
            VStack(alignment: .leading, spacing: 5) {
                Text(record.name).font(.headline).lineLimit(2)
                Text(record.recurrence.label)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            HStack(alignment: .firstTextBaseline) {
                Money(cents: signedAmount(record), colored: true)
                    .font(.title2.weight(.semibold))
                Spacer()
                if let endDate = record.endDate {
                    Text("bis \(Day.label(endDate))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, minHeight: 190, alignment: .leading)
        .kontaCard()
        .contentShape(RoundedRectangle(cornerRadius: 20))
        .accessibilityElement(children: .combine)
    }

    private var emptyTitle: String {
        switch kind {
        case .contract: "Noch keine Verträge"
        case .loan: "Noch keine Kredite"
        case .job: "Noch keine Jobs"
        default: "Noch keine Einträge"
        }
    }

    private var emptyDescription: String {
        switch kind {
        case .contract: "Lege Abos, Versicherungen und laufende Verträge als Karten an."
        case .loan: "Behalte Raten, Restschuld und Laufzeiten im Blick."
        case .job: "Plane Gehalt und weitere regelmäßige Einnahmen."
        default: ""
        }
    }

    private func signedAmount(_ record: FinanceRecord) -> Int64 {
        record.direction == "income" ? abs(record.amount) : -abs(record.amount)
    }

    private func create() {
        var record = FinanceRecord(kind: kind)
        record.direction = kind == .job ? "income" : "expense"
        record.accountID = store.records.first { $0.kind == .account }?.id
        record.categoryID = store.records.first {
            $0.kind == .category && ($0.direction == record.direction || $0.direction == "both")
        }?.id
        creating = record
    }
}

struct RecordListView: View {
    var kind: RecordKind
    @Environment(AppStore.self) private var store
    @State private var selected: FinanceRecord?
    @State private var creating: FinanceRecord?
    @State private var query = ""

    private var records: [FinanceRecord] {
        store.records
            .filter { $0.kind == kind && (query.isEmpty || $0.name.localizedCaseInsensitiveContains(query)) }
            .sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }

    var body: some View {
        List {
            if records.isEmpty {
                ContentUnavailableView(
                    "Noch keine \(kind.plural)",
                    systemImage: kind.symbol,
                    description: Text(kind == .account
                        ? "Lege dein erstes Konto an, um Vermögen und Zahlungen zu planen."
                        : "Lege deinen ersten Eintrag an.")
                )
            }
            ForEach(records) { record in
                Button { selected = record } label: {
                    RecordRow(record: record, subtitle: kind == .account ? record.bank : nil)
                }
                .buttonStyle(.plain)
            }
        }
        .listStyle(.inset)
        .searchable(text: $query, prompt: "Suchen")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { creating = FinanceRecord(kind: kind) } label: {
                    Label("Neu", systemImage: "plus")
                }
                .disabled(!store.canWrite)
            }
        }
        .sheet(item: $selected) { record in
            NavigationStack { RecordDetailView(record: record) }
                .frame(idealWidth: 560, idealHeight: 620)
        }
        .sheet(item: $creating) { record in
            NavigationStack { RecordEditor(record: record) }
                .frame(idealWidth: 580, idealHeight: 680)
        }
    }
}
