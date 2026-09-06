import SwiftUI

struct AuthView: View {
    @Environment(AppStore.self) private var store
    @State private var register = false
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""
    @State private var showReset = false
    var body: some View {
        @Bindable var store = store
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Dein Geld.\nEin guter Plan.").font(.system(.largeTitle, design: .rounded, weight: .bold))
                    Text("Mehr Überblick. Mehr Möglichkeiten.\nFinanzen, die ihr gemeinsam versteht.").foregroundStyle(.secondary)
                }
                Picker("Anmeldung", selection: $register) { Text("Anmelden").tag(false); Text("Konto erstellen").tag(true) }.pickerStyle(.segmented)
                VStack(spacing: 16) {
                    if register { TextField("Dein Name", text: $name).textContentType(.name) }
                    TextField("E-Mail", text: $email).textContentType(.emailAddress)
                        #if os(iOS)
                        .keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled()
                        #endif
                    SecureField(register ? "Passwort · mindestens 12 Zeichen" : "Passwort", text: $password).textContentType(register ? .newPassword : .password)
                    Button {
                        Task { await store.perform { try await store.login(name: name, email: email, password: password, register: register) } }
                    } label: {
                        HStack { Spacer(); if store.busy { ProgressView().controlSize(.small) }; Text(register ? "Konto erstellen" : "Anmelden"); Spacer() }.padding(.vertical, 6)
                    }.buttonStyle(.borderedProminent).disabled(store.busy || email.isEmpty || password.isEmpty)
                    Button("Passwort vergessen?") { showReset = true }.font(.subheadline)
                }.textFieldStyle(.roundedBorder).controlSize(.large)
                DisclosureGroup("Server verbinden") {
                    TextField("https://api.deine-domain.de", text: $store.server)
                        .textFieldStyle(.roundedBorder).padding(.top, 8)
                        #if os(iOS)
                        .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                        #endif
                    Text("Die Adresse deiner Konta-API. Deine Anmeldung wird sicher im Apple-Schlüsselbund gespeichert.").font(.caption).foregroundStyle(.secondary)
                }.font(.subheadline)
                Button { store.startDemo() } label: { Label("Konta kennenlernen", systemImage: "play.circle") }.frame(maxWidth: .infinity)
            }.padding(32).frame(maxWidth: 460).frame(maxWidth: .infinity)
        }
        .onAppear {
            if store.pendingPasswordReset {
                showReset = true
                store.pendingPasswordReset = false
            }
        }
        .onChange(of: store.pendingPasswordReset) { _, requested in
            if requested {
                showReset = true
                store.pendingPasswordReset = false
            }
        }
        .sheet(isPresented: $showReset) { NavigationStack { PasswordResetView() }.frame(idealWidth: 450, idealHeight: 480) }
    }
}
struct PasswordResetView: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var email = ""
    @State private var code = ""
    @State private var password = ""
    @State private var requested = false
    var body: some View {
        Form {
            Section {
                if !requested {
                    TextField("E-Mail", text: $email)
                    BusyButton(title: "Code anfordern") { await store.perform {
                        let _: EmptyResponse = try await store.client().send("auth/forgot", body: ["email": email])
                        requested = true
                    } }
                } else {
                    Text("Falls ein Konto existiert, ist ein Code unterwegs. Er gilt eine Stunde.").foregroundStyle(.secondary)
                    TextField("Code aus der E-Mail", text: $code)
                    SecureField("Neues Passwort · mindestens 12 Zeichen", text: $password)
                    BusyButton(title: "Passwort zurücksetzen") { await store.perform {
                        let _: EmptyResponse = try await store.client().send("auth/reset", body: ["code": code.trimmingCharacters(in: .whitespacesAndNewlines), "password": password])
                        dismiss(); store.message = "Passwort geändert. Du kannst dich jetzt anmelden."
                    } }
                }
            }
        }.formStyle(.grouped).navigationTitle("Passwort zurücksetzen")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Schließen") { dismiss() } } }
    }
}
