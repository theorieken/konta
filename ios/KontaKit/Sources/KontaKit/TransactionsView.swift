import SwiftUI

struct TransactionsView: View {
    var income: Bool
    @Environment(AppStore.self) private var store
    @State private var query = ""
    @State private var filter = "all"
    @State private var mode = "transactions"
    @State private var selected: FinanceRecord?
    @State private var creating: FinanceRecord?
    private var until: Date { Day.calendar.date(byAdding: .day, value: -1, to: Day.addingMonths(store.rangeMonths, to: Day.monthStart(store.rangeStart)))! }
    private var flows: [Movement] {
        FinanceEngine.movements(store.records, through: until).filter {
            (income ? $0.amount >= 0 : $0.amount < 0) && $0.date >= Day.string(Day.monthStart(store.rangeStart)) &&
            (query.isEmpty || $0.name.localizedCaseInsensitiveContains(query)) &&
            (filter == "all" || (filter == "planned" ? $0.planned : !$0.planned))
        }.filter { movement in filter != "review" || store.records.first(where: { $0.id == movement.sourceID })?.needsReview == true }
            .sorted { ($0.date, $0.id) > ($1.date, $1.id) }
    }
    private var sources: [FinanceRecord] {
        store.records.filter { record in
            let matches: Bool = income ? record.kind == .job || (record.kind == .contract && record.direction == "income") : (record.kind == .loan || record.kind == .contract && record.direction != "income")
            return matches && (query.isEmpty || record.name.localizedCaseInsensitiveContains(query))
        }.sorted { $0.name < $1.name }
    }
    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 14) {
                Picker("Ansicht", selection: $mode) { Text("Buchungen").tag("transactions"); Text(income ? "Regelmäßig" : "Verträge & Kredite").tag("sources") }.pickerStyle(.segmented)
                if mode == "transactions" {
                    HStack { Text(Day.label(Day.string(Day.monthStart(store.rangeStart))) + " – " + Day.label(Day.string(until))).font(.caption).foregroundStyle(.secondary); Spacer() }
                    Picker("Status", selection: $filter) { Text("Alle").tag("all"); Text("Gebucht").tag("reality"); Text("Geplant").tag("planned"); Text("Zu prüfen").tag("review") }.pickerStyle(.segmented)
                    HStack { Text("Im Zeitraum").foregroundStyle(.secondary); Spacer(); Money(cents: flows.reduce(0) { $0 + $1.amount }, colored: true).font(.title3.weight(.semibold)) }
                }
            }.padding(20)
            List {
                if mode == "transactions" {
                    if flows.isEmpty { ContentUnavailableView("Noch keine Buchungen", systemImage: "tray", description: Text("Lege eine Transaktion an oder importiere deine Umsätze unter Haushalt.")) }
                    ForEach(flows) { movement in
                        Button { selected = store.records.first { $0.id == movement.sourceID } } label: {
                            HStack(spacing: 12) {
                                Image(systemName: movement.planned ? "calendar" : "arrow.left.arrow.right").foregroundStyle(KontaStyle.accent).frame(width: 32)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(movement.name).font(.body.weight(.medium)).lineLimit(2)
                                    Text(Day.label(movement.date) + (movement.planned ? (movement.date < Day.string(Date()) ? " · Überfällig" : " · Geplant") : " · Gebucht")).font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer(minLength: 8)
                                Money(cents: movement.amount, colored: true).font(.body.weight(.medium))
                            }.padding(.vertical, 6).contentShape(Rectangle())
                        }.buttonStyle(.plain)
                    }
                } else {
                    if sources.isEmpty { ContentUnavailableView("Alles Regelmäßige an einem Ort", systemImage: "repeat", description: Text("Gehälter, Miete, Verträge und Kreditraten fließen automatisch in deinen Plan ein.")) }
                    ForEach(sources) { record in
                        Button { selected = record } label: { RecordRow(record: record, subtitle: record.recurrence.label + (record.active ? "" : " · Pausiert")) }.buttonStyle(.plain)
                    }
                }
            }.listStyle(.plain)
        }.searchable(text: $query, prompt: "Suchen")
            .toolbar { ToolbarItem(placement: .primaryAction) {
                Menu {
                    Button("Transaktion", systemImage: "arrow.left.arrow.right") { create(.transaction) }
                    if income { Button("Regelmäßiges Einkommen", systemImage: "briefcase") { create(.job) } }
                    else { Button("Vertrag", systemImage: "repeat") { create(.contract) }; Button("Kredit", systemImage: "creditcard") { create(.loan) } }
                } label: { Label("Neu", systemImage: "plus") }.disabled(!store.canWrite)
            } }
            .sheet(item: $selected) { record in NavigationStack { RecordDetailView(record: record) }.frame(idealWidth: 560, idealHeight: 650) }
            .sheet(item: $creating) { record in NavigationStack { RecordEditor(record: record) }.frame(idealWidth: 580, idealHeight: 680) }
    }
    private func create(_ kind: RecordKind) {
        var record = FinanceRecord(kind: kind)
        record.direction = income ? "income" : "expense"
        record.accountID = store.records.first { $0.kind == .account }?.id
        record.categoryID = store.records.first { $0.kind == .category && $0.direction == record.direction }?.id
        creating = record
    }
}

struct RecordListView: View {
    var kind: RecordKind
    @Environment(AppStore.self) private var store
    @State private var selected: FinanceRecord?
    @State private var creating: FinanceRecord?
    @State private var query = ""
    var body: some View {
        List {
            ForEach(store.records.filter { $0.kind == kind && (query.isEmpty || $0.name.localizedCaseInsensitiveContains(query)) }.sorted { $0.name < $1.name }) { record in
                Button { selected = record } label: { RecordRow(record: record, subtitle: kind == .account ? record.bank : nil) }.buttonStyle(.plain)
            }
        }.navigationTitle(kind.plural).searchable(text: $query, prompt: "Suchen")
            .toolbar { ToolbarItem(placement: .primaryAction) { Button { creating = FinanceRecord(kind: kind) } label: { Label(kind.label, systemImage: "plus") }.disabled(!store.canWrite) } }
            .sheet(item: $selected) { record in NavigationStack { RecordDetailView(record: record) }.frame(idealWidth: 560, idealHeight: 620) }
            .sheet(item: $creating) { record in NavigationStack { RecordEditor(record: record) }.frame(idealWidth: 580, idealHeight: 680) }
    }
}
