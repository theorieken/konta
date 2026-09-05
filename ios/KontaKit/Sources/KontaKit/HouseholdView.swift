import SwiftUI
import UniformTypeIdentifiers

struct HouseholdView: View {
    @Environment(AppStore.self) private var store
    @State private var newName = ""
    @State private var inviteEmail = ""
    @State private var code = ""
    @State private var transferMember: Member?
    @State private var removeMember: Member?
    var body: some View {
        List {
            if !store.demo && store.session?.user.verified == false { verification }
            Section("Deine Haushalte") {
                ForEach(store.households) { household in
                    Button { Task { await store.selectHousehold(household.id) } } label: {
                        HStack {
                            Label(household.name, systemImage: "house")
                            Spacer()
                            if household.id == store.selectedHouseholdID { Image(systemName: "checkmark").foregroundStyle(KontaStyle.accent) }
                        }.padding(.vertical, 4)
                    }.buttonStyle(.plain)
                }
                if !store.demo {
                    HStack {
                        TextField("Neuer Haushalt", text: $newName)
                        Button { Task { await store.perform { try await store.createHousehold(newName); newName = "" } } } label: { Image(systemName: "plus.circle.fill") }
                            .accessibilityLabel("Haushalt erstellen").help("Haushalt erstellen").disabled(store.busy || newName.trimmingCharacters(in: .whitespaces).isEmpty || store.offline)
                    }
                }
            }
            if !store.invitations.isEmpty {
                Section("Einladungen für dich") {
                    ForEach(store.invitations) { invitation in
                        VStack(alignment: .leading, spacing: 10) {
                            Text(invitation.householdName).font(.headline)
                            Text("Du wurdest eingeladen, diesen Haushalt gemeinsam zu planen.").font(.subheadline).foregroundStyle(.secondary)
                            HStack {
                                BusyButton(title: "Annehmen") { await respond(invitation, accept: true) }.buttonStyle(.borderedProminent)
                                BusyButton(title: "Ablehnen") { await respond(invitation, accept: false) }
                            }
                        }.padding(.vertical, 6)
                    }
                }
            }
            if store.household != nil {
                Section("Finanzen verwalten") {
                    NavigationLink { RecordListView(kind: .account) } label: { Label("Konten", systemImage: "building.columns") }
                    NavigationLink { RecordListView(kind: .category) } label: { Label("Kategorien & Budgets", systemImage: "square.grid.2x2") }
                    NavigationLink { ImportView() } label: { Label("CSV-Import", systemImage: "square.and.arrow.down") }
                    NavigationLink { SettingsView() } label: { Label("Einstellungen", systemImage: "gearshape") }
                }
                Section("Gemeinsam planen") {
                    ForEach(store.snapshot?.members ?? []) { member in
                        HStack {
                            VStack(alignment: .leading, spacing: 3) { Text(member.name); Text(member.email).font(.caption).foregroundStyle(.secondary) }
                            Spacer()
                            Text(member.role == "owner" ? "Leitung" : "Mitglied").font(.caption).foregroundStyle(.secondary)
                            if store.isOwner && member.id != store.session?.user.id {
                                Menu { Button("Leitung übertragen") { transferMember = member }; Button("Entfernen", role: .destructive) { removeMember = member } } label: { Image(systemName: "ellipsis.circle") }
                                    .help("Mitglied verwalten").accessibilityLabel("Mitglied verwalten")
                            }
                        }
                    }
                    if store.isOwner && !store.demo {
                        TextField("E-Mail-Adresse", text: $inviteEmail)
                            #if os(iOS)
                            .keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled()
                            #endif
                        BusyButton(title: "Einladen", systemImage: "envelope") { await store.perform { try await store.invite(inviteEmail); inviteEmail = "" } }
                            .disabled(inviteEmail.isEmpty || !store.canWrite)
                    }
                }
                if store.isOwner, let household = store.household, !(store.snapshot?.invitations.isEmpty ?? true) {
                    Section("Versendete Einladungen") {
                        ForEach(store.snapshot?.invitations ?? []) { invitation in
                            HStack {
                                VStack(alignment: .leading) { Text(invitation.email); Text(invitation.status == "expired" ? "Abgelaufen" : "Offen").font(.caption).foregroundStyle(.secondary) }
                                Spacer()
                                BusyButton(title: "Widerrufen") { await store.perform { try await store.command("households/\(household.id)/invitations/\(invitation.id)", method: "DELETE", body: [String: String]()) } }
                            }
                        }
                    }
                }
            } else {
                Section { NavigationLink("Profil & Einstellungen") { SettingsView() } }
            }
            if !store.notifications.isEmpty {
                Section("Mitteilungen") {
                    ForEach(store.notifications) { notification in
                        Button { Task { await store.perform { try await store.command("notifications/\(notification.id)", body: [String: String]()) } } } label: {
                            HStack(alignment: .top) {
                                Image(systemName: notification.read ? "bell" : "bell.badge").foregroundStyle(KontaStyle.accent)
                                VStack(alignment: .leading, spacing: 5) { Text(notification.title).font(.headline); Text(notification.body).font(.subheadline).foregroundStyle(.secondary) }
                            }
                        }.buttonStyle(.plain)
                    }
                }
            }
        }.listStyle(.inset)
            .confirmationDialog("Haushaltsleitung übertragen?", isPresented: Binding(get: { transferMember != nil }, set: { if !$0 { transferMember = nil } }), titleVisibility: .visible) {
                if let member = transferMember, let household = store.household {
                    Button("An \(member.name) übertragen") { Task { await store.perform { try await store.command("households/\(household.id)/transfer", body: ["userID": member.id]); transferMember = nil } } }
                }
            }
            .confirmationDialog("Mitglied entfernen?", isPresented: Binding(get: { removeMember != nil }, set: { if !$0 { removeMember = nil } }), titleVisibility: .visible) {
                if let member = removeMember, let household = store.household {
                    Button("\(member.name) entfernen", role: .destructive) { Task { await store.perform { try await store.command("households/\(household.id)/members/\(member.id)", method: "DELETE", body: [String: String]()); removeMember = nil } } }
                }
            }
    }
    private var verification: some View {
        Section {
            Text("Bestätige deine E-Mail-Adresse, um andere Personen einzuladen und Einladungen anzunehmen.").font(.subheadline).foregroundStyle(.secondary)
            TextField("Bestätigungscode aus der E-Mail", text: $code)
            HStack {
                BusyButton(title: "Bestätigen") { await store.perform { try await store.command("auth/verify", body: ["code": code.trimmingCharacters(in: .whitespacesAndNewlines)]); code = "" } }.disabled(code.isEmpty)
                BusyButton(title: "Code erneut senden") { await store.perform { try await store.command("auth/resend", body: [String: String]()); store.message = "Ein neuer Bestätigungscode ist unterwegs." } }
            }
        } header: { Label("E-Mail bestätigen", systemImage: "envelope.badge") }
    }
    private func respond(_ invitation: Invitation, accept: Bool) async {
        await store.perform { try await store.command("invitations/\(invitation.id)", body: ["accept": accept]); if accept { await store.selectHousehold(invitation.householdID) } }
    }
}

struct ImportView: View {
    @Environment(AppStore.self) private var store
    @State private var account = ""
    @State private var picking = false
    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 12) {
                    Image(systemName: "tray.and.arrow.down").font(.largeTitle).foregroundStyle(KontaStyle.accent)
                    Text("Deine Umsätze. Schon sortiert.").font(.title2.weight(.semibold))
                    Text("Wähle einen CSV-Export deiner Bank. Konta erkennt die Spalten und überspringt bereits importierte Buchungen.").foregroundStyle(.secondary)
                }.padding(.vertical, 12)
                Picker("Zielkonto", selection: $account) {
                    Text("Bitte wählen").tag("")
                    ForEach(store.records.filter { $0.kind == .account }) { Text($0.name).tag($0.id) }
                }
                Button { picking = true } label: { Label("CSV auswählen", systemImage: "folder") }.disabled(account.isEmpty || !store.canWrite)
                Text("Bis 10 MB und 2.000 Buchungen pro Datei. UTF-8 und Windows-1252, Komma, Semikolon oder Tabulator.").font(.caption).foregroundStyle(.secondary)
                if store.busy { ProgressView("Wird verarbeitet …") }
            }
            Section {
                Text("Stichwörter ordnen Buchungen ohne KI zu. Nach deiner Freigabe kann KI ungeklärte Buchungen kategorisieren. Manuell gewählte Kategorien bleiben erhalten.").font(.subheadline).foregroundStyle(.secondary)
                BusyButton(title: "Offene Buchungen mit KI zuordnen", systemImage: "sparkles") { await store.perform { try await store.classify() } }
                    .disabled(!store.canWrite || store.household?.aiEnabled != true)
            } header: { Text("KI-Kategorisierung") }
            Section("Importverlauf") {
                ForEach(store.snapshot?.uploads ?? []) { upload in
                    VStack(alignment: .leading, spacing: 5) {
                        Label(upload.name, systemImage: "doc.text")
                        Text("\(upload.imported) importiert · \(upload.duplicates) Duplikate").font(.caption).foregroundStyle(.secondary)
                    }.padding(.vertical, 4)
                }
            }
        }.navigationTitle("CSV-Import")
            .onAppear { account = store.records.first { $0.kind == .account }?.id ?? "" }
            .fileImporter(isPresented: $picking, allowedContentTypes: [.commaSeparatedText, .plainText]) { result in
                switch result { case .success(let url): Task { await store.perform { try await store.upload(url, account: account) } }; case .failure(let error): store.handle(error) }
            }
    }
}

struct SnapshotDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json] }
    var data: Data
    init(data: Data) { self.data = data }
    init(configuration: ReadConfiguration) throws { data = configuration.file.regularFileContents ?? Data() }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}
