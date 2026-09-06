import SwiftUI

struct RecordEditor: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State var record: FinanceRecord
    @State private var amount = ""
    @State private var principal = ""
    @State private var budget = ""
    @State private var interest = ""
    @State private var tags = ""
    @State private var keywords = ""
    @State private var hasEnd = false
    @State private var localError: String?
    private var hasRelations: Bool { record.kind == .transaction || record.kind.isRecurring }
    var body: some View {
        Form {
            Section("Allgemein") {
                TextField("Name", text: $record.name)
                if record.kind == .transaction || record.kind == .contract || record.kind == .category {
                    Picker("Richtung", selection: $record.direction) {
                        Text("Ausgabe").tag("expense"); Text("Einnahme").tag("income")
                        if record.kind == .category { Text("Beides").tag("both") }
                    }
                }
                if record.kind != .category {
                    TextField(record.kind == .account ? "Startsaldo (€)" : record.kind == .loan ? "Rate (€)" : "Betrag (€)", text: $amount)
                    DatePicker(record.kind == .account ? "Startsaldo am" : record.kind.isRecurring ? "Beginn" : "Buchungsdatum", selection: dateBinding, displayedComponents: .date)
                }
                if hasRelations { relations }
            }
            if record.kind == .transaction {
                Section("Buchung") {
                    Picker("Status", selection: $record.state) { Text("Gebucht").tag("reality"); Text("Geplant").tag("planned") }
                    TextField("Empfänger / Absender", text: $record.counterparty)
                    Toggle("Noch zu prüfen", isOn: $record.needsReview)
                }
            }
            if record.kind.isRecurring { recurring }
            if record.kind == .account { account }
            if record.kind == .loan { loan }
            if record.kind == .category {
                Section("Zuordnung & Budget") {
                    TextField("Stichwörter · durch Komma getrennt", text: $keywords)
                    TextField("Monatsbudget (€)", text: $budget)
                }
            }
            Section {
                DisclosureGroup("Weitere Details") {
                    TextField("Tags · durch Komma getrennt", text: $tags)
                    TextField("Notizen", text: $record.notes, axis: .vertical).lineLimit(3...7)
                }
            }
            if let localError { Section { Text(localError).foregroundStyle(.secondary) } }
        }.formStyle(.grouped).navigationTitle(record.version == 0 ? "Neues " + record.kind.label : record.kind.label + " bearbeiten")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Abbrechen") { dismiss() }.disabled(store.busy) }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") { Task { await save() } }.disabled(store.busy || record.name.trimmingCharacters(in: .whitespaces).isEmpty || store.demo || store.offline)
                        .keyboardShortcut(.defaultAction)
                }
            }.interactiveDismissDisabled(store.busy)
            .onAppear {
                amount = Euro.input(record.kind == .account ? record.amount : abs(record.amount))
                principal = Euro.input(record.principal); budget = Euro.input(record.budget)
                interest = Euro.input(Int64(record.interestBasisPoints))
                tags = record.tags.joined(separator: ", "); keywords = record.keywords.joined(separator: ", ")
                hasEnd = record.endDate != nil
                if record.kind == .transaction { record.direction = record.amount > 0 ? "income" : (record.amount < 0 ? "expense" : record.direction) }
            }
    }
    private var dateBinding: Binding<Date> { Binding(get: { Day.date(record.date) }, set: { record.date = Day.string($0) }) }
    private var relations: some View {
        Group {
            Picker("Konto", selection: $record.accountID) {
                Text("Bitte wählen").tag(String?.none)
                ForEach(store.records.filter { $0.kind == .account }) { Text($0.name).tag(Optional($0.id)) }
            }
            Picker("Kategorie", selection: $record.categoryID) {
                Text("Bitte wählen").tag(String?.none)
                ForEach(store.records.filter { $0.kind == .category }.sorted { $0.name < $1.name }) { Text($0.name).tag(Optional($0.id)) }
            }
        }
    }
    private var recurring: some View {
        Section("Wiederholung") {
            Picker("Intervall", selection: $record.recurrence) { ForEach(Recurrence.allCases) { Text($0.label).tag($0) } }
            if record.recurrence != .once {
                Stepper("Intervall-Faktor: \(record.intervalCount)", value: $record.intervalCount, in: 1...60)
                if record.recurrence.months != nil { Stepper("Tag im Monat: \(record.dayOfMonth)", value: $record.dayOfMonth, in: 1...31) }
            }
            Toggle("Befristet", isOn: $hasEnd)
            if hasEnd {
                DatePicker("Ende", selection: Binding(get: { Day.date(record.endDate ?? record.date) }, set: { record.endDate = Day.string($0) }), in: Day.date(record.date)..., displayedComponents: .date)
                if record.kind == .contract { Stepper("Kündigungsfrist: \(record.cancellationDays) Tage", value: $record.cancellationDays, in: 0...3650) }
            }
            Toggle("Aktiv", isOn: $record.active)
        }
    }
    private var account: some View {
        Section("Konto") {
            Picker("Art", selection: $record.accountType) {
                Text("Girokonto").tag("checking"); Text("Sparkonto").tag("savings"); Text("Kreditkarte").tag("credit"); Text("Bargeld").tag("cash"); Text("Depot").tag("investment")
            }
            TextField("Bank", text: $record.bank)
            TextField("IBAN", text: $record.iban)
            Toggle("Im Gesamtvermögen", isOn: $record.includeInNetWorth)
            Toggle("Aktiv", isOn: $record.active)
        }
    }
    private var loan: some View {
        Section {
            TextField("Restschuld bei Beginn (€)", text: $principal)
            TextField("Zinssatz pro Jahr (%)", text: $interest)
        } header: { Text("Kredit") } footer: { Text("Die Vorschau rechnet mit konstantem Zins, fester Rate und Zinsbelastung pro Zahlungsintervall. Sondertilgungen als neue Restschuld mit neuem Beginn erfassen.") }
    }
    private func save() async {
        do {
            var result = record
            guard let cents = Euro.parse(amount.isEmpty ? "0" : amount), let debt = Euro.parse(principal.isEmpty ? "0" : principal), let monthlyBudget = Euro.parse(budget.isEmpty ? "0" : budget), let rate = Euro.parse(interest.isEmpty ? "0" : interest) else {
                throw APIError(status: 0, message: "Bitte gültige Beträge mit maximal zwei Nachkommastellen eingeben.")
            }
            if result.kind != .account && cents < 0 { throw APIError(status: 0, message: "Bitte den Betrag positiv eingeben und die Richtung auswählen.") }
            result.amount = result.kind == .transaction && result.direction == "expense" ? -cents : cents
            result.principal = debt; result.budget = monthlyBudget; result.interestBasisPoints = Int(rate)
            result.tags = tags.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
            result.keywords = keywords.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
            result.endDate = hasEnd ? (result.endDate ?? result.date) : nil
            if result.kind == .transaction { result.categorySource = "manual"; result.confidence = nil }
            if result.state == "planned" { result.matchedPlanKey = nil }
            store.busy = true; defer { store.busy = false }
            try await store.save(result)
            dismiss()
        } catch { localError = error.localizedDescription }
    }
}

struct RecordDetailView: View {
    let record: FinanceRecord
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var editing = false
    @State private var deleting = false
    @State private var matching = false
    private var current: FinanceRecord { store.records.first { $0.id == record.id } ?? record }
    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 12) {
                    Label(current.kind.label, systemImage: current.kind.symbol).font(.subheadline).foregroundStyle(KontaStyle.accent)
                    Text(current.name).font(.system(.title, design: .rounded, weight: .semibold))
                    if current.kind != .category { Money(cents: current.amount, colored: current.kind == .transaction).font(.largeTitle.weight(.semibold)) }
                }.padding(.vertical, 12)
            }
            Section("Details") {
                if current.kind != .category { LabeledContent(current.kind == .account ? "Startsaldo am" : "Datum", value: Day.label(current.date)) }
                if let account = store.records.first(where: { $0.id == current.accountID }) { LabeledContent("Konto", value: account.name) }
                if let category = store.records.first(where: { $0.id == current.categoryID }) { LabeledContent("Kategorie", value: category.name) }
                if current.kind == .transaction {
                    LabeledContent("Status", value: current.state == "planned" ? "Geplant" : "Gebucht")
                    LabeledContent("Zuordnung", value: ["manual": "Manuell", "ai": "KI", "keyword": "Stichwörter", "plan": "Planabgleich"][current.categorySource] ?? current.categorySource)
                    if let confidence = current.confidence { LabeledContent("Sicherheit", value: confidence.formatted(.percent.precision(.fractionLength(0)))) }
                    if current.needsReview { Label("Bitte Kategorie prüfen", systemImage: "sparkles").foregroundStyle(KontaStyle.accent) }
                }
                if current.kind.isRecurring { LabeledContent("Wiederholung", value: current.recurrence.label); LabeledContent("Aktiv", value: current.active ? "Ja" : "Nein") }
                if let end = current.endDate { LabeledContent("Ende", value: Day.label(end)) }
                if current.cancellationDays > 0 { LabeledContent("Kündigungsfrist", value: "\(current.cancellationDays) Tage") }
                if !current.bank.isEmpty { LabeledContent("Bank", value: current.bank) }
                if !current.iban.isEmpty { LabeledContent("IBAN", value: current.iban).textSelection(.enabled) }
                if !current.counterparty.isEmpty { LabeledContent("Empfänger / Absender", value: current.counterparty) }
                if current.kind == .account { LabeledContent("Saldo heute") { Money(cents: FinanceEngine.balance(records: store.records, at: Date(), includePlanned: false, accountID: current.id)) } }
                if current.kind == .loan { LabeledContent("Restschuld bei Beginn") { Money(cents: current.principal) }; LabeledContent("Zinssatz", value: Euro.input(Int64(current.interestBasisPoints)) + " %") }
                if current.budget > 0 { LabeledContent("Monatsbudget") { Money(cents: current.budget) } }
                if !current.keywords.isEmpty { LabeledContent("Stichwörter", value: current.keywords.joined(separator: ", ")) }
            }
            if !current.notes.isEmpty { Section("Notizen") { Text(current.notes).textSelection(.enabled) } }
            if !current.tags.isEmpty { Section("Tags") { Text(current.tags.map { "#" + $0 }.joined(separator: "  ")).foregroundStyle(KontaStyle.accent) } }
            if current.kind == .transaction && current.state == "reality" {
                Section("Planabgleich") {
                    if let key = current.matchedPlanKey {
                        Text("Mit einer geplanten Zahlung verknüpft. Die Planung zählt diese Zahlung nur einmal.").font(.subheadline).foregroundStyle(.secondary)
                        Text(key).font(.caption2.monospaced()).textSelection(.enabled)
                        BusyButton(title: "Verknüpfung lösen") { await store.perform { var updated = current; updated.matchedPlanKey = nil; try await store.save(updated) } }.disabled(!store.canWrite)
                    } else { Button("Mit geplanter Zahlung abgleichen") { matching = true }.disabled(!store.canWrite) }
                }
            }
            if current.kind == .transaction && current.state == "planned" {
                BusyButton(title: "Als gebucht markieren") { await store.perform { var updated = current; updated.state = "reality"; try await store.save(updated) } }.disabled(!store.canWrite)
            }
            if let created = current.createdAt { Section { Text("Erstellt: \(created)\nVersion \(current.version)").font(.caption).foregroundStyle(.secondary) } }
            Section { Button("Löschen", role: .destructive) { deleting = true }.disabled(!store.canWrite) }
        }.navigationTitle(current.kind.label)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Schließen") { dismiss() } }
                ToolbarItem(placement: .primaryAction) { Button("Bearbeiten") { editing = true }.disabled(!store.canWrite) }
            }
            .sheet(isPresented: $editing) { NavigationStack { RecordEditor(record: current) }.frame(idealWidth: 580, idealHeight: 680) }
            .sheet(isPresented: $matching) { NavigationStack { MatchPlanView(record: current) }.frame(idealWidth: 540, idealHeight: 500) }
            .confirmationDialog("„\(current.name)“ löschen?", isPresented: $deleting, titleVisibility: .visible) {
                Button("Löschen", role: .destructive) { Task { await store.perform { try await store.delete(current); dismiss() } } }
            } message: { Text("Der Eintrag wird entfernt. Buchungen bleiben beim Löschen einer regelmäßigen Quelle erhalten.") }
    }
}

struct MatchPlanView: View {
    var record: FinanceRecord
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    private var candidates: [Movement] {
        FinanceEngine.movements(store.records, through: Day.addingMonths(1, to: Day.date(record.date)), today: Day.date(record.date)).filter {
            $0.planned && $0.accountID == record.accountID && $0.amount.signum() == record.amount.signum() &&
            abs(Day.date($0.date).timeIntervalSince(Day.date(record.date))) <= 7 * 86400 &&
            abs(Double($0.amount - record.amount)) <= abs(Double(record.amount)) * 0.15
        }
    }
    var body: some View {
        List {
            Text("Wähle den passenden Plan. Vorschläge liegen höchstens sieben Tage und 15 % vom Buchungsbetrag entfernt.").font(.subheadline).foregroundStyle(.secondary)
            if candidates.isEmpty { ContentUnavailableView("Kein passender Plan", systemImage: "calendar.badge.checkmark") }
            ForEach(candidates) { candidate in
                Button {
                    Task { await store.perform {
                        var updated = record; updated.matchedPlanKey = candidate.planKey
                        try await store.save(updated); dismiss()
                    } }
                } label: { HStack { VStack(alignment: .leading) { Text(candidate.name); Text(Day.label(candidate.date)).font(.caption).foregroundStyle(.secondary) }; Spacer(); Money(cents: candidate.amount) } }
                    .disabled(store.busy)
            }
        }.navigationTitle("Plan abgleichen").toolbar { ToolbarItem(placement: .cancellationAction) { Button("Abbrechen") { dismiss() } } }
    }
}
