import SwiftUI
import UserNotifications

public struct SettingsView: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var newHouseholdName = ""
    @State private var addingHousehold = false
    @State private var householdName = ""
    @State private var horizon = 24
    @State private var aiEnabled = false
    @State private var aiModel = "gpt-4.1-mini"
    @State private var export = false
    @State private var document: SnapshotDocument?
    @State private var householdConfirmation = ""
    @State private var password = ""
    @State private var deleteAccount = false
    @State private var deleteHousehold = false
    @State private var leaveHousehold = false
    @State private var showPrivacy = false
    public init() {}
    public var body: some View {
        Form {
            profile
            households
            if let household = store.household {
                householdSettings(household)
                Section("Verwalten") {
                    NavigationLink {
                        HouseholdView()
                    } label: {
                        Label("Mitglieder & Einladungen", systemImage: "person.2")
                    }
                    NavigationLink {
                        RecordListView(kind: .category)
                    } label: {
                        Label("Kategorien & Budgets", systemImage: "square.grid.2x2")
                    }
                    NavigationLink {
                        ImportView()
                    } label: {
                        Label("CSV-Import", systemImage: "square.and.arrow.down")
                    }
                }
                intelligence(household)
                Section("Daten") {
                    Button("Haushalt als JSON exportieren", systemImage: "square.and.arrow.up") {
                        do { if let snapshot = store.snapshot { let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]; document = SnapshotDocument(data: try encoder.encode(snapshot)); export = true } }
                        catch { store.handle(error) }
                    }
                    Text("Der Export enthält die Finanzdaten und Mitglieder dieses Haushalts. Bewahre ihn sicher auf.").font(.caption).foregroundStyle(.secondary)
                }
            }
            Section("Apple-Mitteilungen") {
                BusyButton(title: NativeNotifications.shared.enabled ? "Mitteilungen sind aktiviert" : "Mitteilungen aktivieren", systemImage: "bell.badge") {
                    await store.perform {
                        try await NativeNotifications.shared.requestAuthorization()
                        await store.registerDevice()
                        if let id = store.selectedHouseholdID { try await NativeNotifications.shared.schedule(records: store.records, household: id) }
                        if !NativeNotifications.shared.enabled { store.message = "Du kannst Mitteilungen in den Systemeinstellungen für Konta erlauben." }
                    }
                }.disabled(store.demo)
                Text("Einladungen und Kündigungsfristen erscheinen als native Apple-Mitteilungen. Finanzbeträge werden nicht auf dem Sperrbildschirm angezeigt.").font(.caption).foregroundStyle(.secondary)
            }
            Section("Konta") {
                Button("Datenschutz") { showPrivacy = true }
                LabeledContent("Version", value: "1.0 (1)")
                LabeledContent("Server", value: store.server).font(.caption)
                BusyButton(title: store.demo ? "Vorschau beenden" : "Abmelden", systemImage: "rectangle.portrait.and.arrow.right") { await store.perform { try await store.logout(); dismiss() } }
            }
            if !store.demo { danger }
        }.formStyle(.grouped).navigationTitle("Einstellungen")
            .onAppear {
                name = store.session?.user.name ?? ""
                if let household = store.household {
                    householdName = household.name
                    horizon = household.horizon; aiEnabled = household.aiEnabled; aiModel = household.aiModel
                }
            }
            .onChange(of: store.household?.id) { _, _ in
                if let household = store.household {
                    householdName = household.name
                    horizon = household.horizon
                    aiEnabled = household.aiEnabled
                    aiModel = household.aiModel
                }
            }
            .fileExporter(isPresented: $export, document: document, contentType: .json, defaultFilename: "Konta-\(Day.string(Date()))") { result in if case .failure(let error) = result { store.handle(error) } }
            .sheet(isPresented: $showPrivacy) { NavigationStack { PrivacyView() }.frame(idealWidth: 540, idealHeight: 580) }
            .confirmationDialog("Benutzerkonto endgültig löschen?", isPresented: $deleteAccount, titleVisibility: .visible) {
                Button("Benutzerkonto löschen", role: .destructive) { Task { await store.perform {
                    let _: EmptyResponse = try await store.client().send("me", method: "DELETE", body: ["password": password]); store.clearSession(); dismiss()
                } } }
            } message: { Text("Deine Anmeldung und Mitgliedschaften werden gelöscht. Übertrage zuvor die Leitung deiner Haushalte oder lösche sie.") }
            .confirmationDialog("Haushalt endgültig löschen?", isPresented: $deleteHousehold, titleVisibility: .visible) {
                if let household = store.household {
                    Button("Haushalt und alle Daten löschen", role: .destructive) { Task { await store.perform { try await store.command("households/\(household.id)", method: "DELETE", body: ["confirmation": householdConfirmation]); dismiss() } } }
                }
            } message: { Text("Alle Konten, Buchungen, Dateien und Einladungen dieses Haushalts werden für alle Mitglieder gelöscht.") }
            .confirmationDialog("Haushalt verlassen?", isPresented: $leaveHousehold, titleVisibility: .visible) {
                if let household = store.household, let user = store.session?.user {
                    Button("Haushalt verlassen", role: .destructive) { Task { await store.perform { try await store.command("households/\(household.id)/members/\(user.id)", method: "DELETE", body: [String: String]()); dismiss() } } }
                }
            }
    }
    private var profile: some View {
        Section("Dein Profil") {
            TextField("Name", text: $name)
            LabeledContent("E-Mail", value: store.session?.user.email ?? "")
            BusyButton(title: "Profil speichern") { await store.perform {
                let _: User = try await store.client().send("me", method: "PATCH", body: ["name": name]); try await store.refresh(); store.message = "Profil gespeichert."
            } }.disabled(!store.canWrite)
        }
    }
    private var households: some View {
        Section("Haushalte") {
            ForEach(store.households) { household in
                Button {
                    Task { await store.selectHousehold(household.id) }
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(household.name).foregroundStyle(.primary)
                            Text(household.role == "owner" ? "Leitung" : "Mitglied")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if household.id == store.selectedHouseholdID {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(KontaStyle.accent)
                        }
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
            if !store.demo {
                if addingHousehold {
                    HStack {
                        TextField("Name des Haushalts", text: $newHouseholdName)
                            .textFieldStyle(.roundedBorder)
                        Button("Hinzufügen") {
                            Task {
                                await store.perform {
                                    try await store.createHousehold(newHouseholdName)
                                    newHouseholdName = ""
                                    addingHousehold = false
                                }
                            }
                        }
                        .disabled(newHouseholdName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || !store.canWrite)
                        Button("Abbrechen") {
                            newHouseholdName = ""
                            addingHousehold = false
                        }
                    }
                } else {
                    Button("Haushalt hinzufügen", systemImage: "plus") { addingHousehold = true }
                        .disabled(store.offline)
                }
            }
            if store.households.count > 1 {
                Text("Der aktive Haushalt bestimmt, welche Finanzdaten gerade angezeigt werden.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
    private func householdSettings(_ household: Household) -> some View {
        Section("Aktueller Haushalt") {
            TextField("Haushaltsname", text: $householdName)
            Stepper("Planungshorizont: \(horizon) Monate", value: $horizon, in: 1...120)
            BusyButton(title: "Haushalt speichern") { await store.perform {
                var updated = household
                updated.name = householdName.trimmingCharacters(in: .whitespacesAndNewlines)
                updated.horizon = horizon
                try await store.updateHousehold(updated)
                store.message = "Haushalt gespeichert."
            } }
        }.disabled(!store.isOwner || !store.canWrite)
    }
    private func intelligence(_ household: Household) -> some View {
        Section {
            DisclosureGroup("Optionale KI-Kategorisierung") {
                Toggle("KI-Kategorisierung erlauben", isOn: $aiEnabled)
                TextField("OpenAI-Modell", text: $aiModel)
                Text("Nach deiner Freigabe können Buchungstext, Gegenpartei und Betrag ausgewählter Buchungen zur Kategorisierung übertragen werden. Kontonummern und IBAN-Felder werden nicht gesendet.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                BusyButton(title: "KI-Einstellungen speichern") { await store.perform {
                    var updated = household; updated.aiEnabled = aiEnabled; updated.aiModel = aiModel
                    try await store.updateHousehold(updated); store.message = "KI-Einstellungen gespeichert."
                } }
            }
        } header: { Text("Automatisierung") }
            .disabled(!store.isOwner || !store.canWrite)
    }
    private var danger: some View {
        Section("Zugriff & Löschen") {
            if let household = store.household {
                if store.isOwner {
                    TextField("Haushaltsname zur Bestätigung", text: $householdConfirmation)
                    Button("Haushalt löschen", role: .destructive) { deleteHousehold = true }.disabled(householdConfirmation != household.name || !store.canWrite)
                } else { Button("Haushalt verlassen", role: .destructive) { leaveHousehold = true }.disabled(!store.canWrite) }
            }
            SecureField("Passwort zur Kontolöschung", text: $password)
            Button("Benutzerkonto löschen", role: .destructive) { deleteAccount = true }.disabled(password.isEmpty || !store.canWrite)
        }
    }
}

struct PrivacyView: View {
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        List {
            Section("Deine Daten") { Text("Konta speichert deine Konten, Buchungen, Haushalte, Mitgliedschaften und Importe auf dem von dir konfigurierten Server. Haushaltsmitglieder können die gemeinsamen Finanzdaten sehen und bearbeiten. Die Haushaltsleitung verwaltet Einladungen und Einstellungen.") }
            Section("Auf deinem Gerät") { Text("Anmeldedaten liegen im Apple-Schlüsselbund. Für den Offline-Lesezugriff wird der zuletzt geladene Haushalt verschlüsselt gespeichert. Beim Abmelden werden diese lokalen Daten gelöscht.") }
            Section("KI ist freiwillig") { Text("Ohne Freigabe werden Buchungen nur über Stichwörter zugeordnet. Nach Aktivierung können Buchungstexte, Gegenparteien und Beträge für die Kategorisierung an OpenAI gesendet werden. API-Anfragen verwenden store=false. Die Datenverarbeitung durch OpenAI richtet sich nach dessen Bedingungen.") }
            Section("Mitteilungen") { Text("Für Push-Mitteilungen wird das Geräte-Token beim Server hinterlegt und zur Zustellung über Apple verwendet. Der Inhalt enthält keine Kontostände oder Buchungsbeträge. Kündigungsfristen werden lokal über Apple-Mitteilungen erinnert.") }
            Section("Export & Löschen") { Text("Du kannst deinen Haushalt als JSON exportieren und dein Benutzerkonto in den Einstellungen löschen. Haushaltsdaten bleiben für andere Mitglieder erhalten, bis die Haushaltsleitung den Haushalt löscht. Gelöschte einzelne Finanzobjekte werden nach 90 Tagen endgültig bereinigt, wenn der Wartungsjob eingerichtet ist.") }
        }.navigationTitle("Datenschutz").toolbar { ToolbarItem(placement: .confirmationAction) { Button("Fertig") { dismiss() } } }
    }
}
