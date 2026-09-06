import SwiftUI

public enum Destination: String, CaseIterable, Identifiable, Sendable {
    case overview, savings, payments, contracts, loans, jobs, accounts, settings

    public var id: String { rawValue }
    static let primary: [Destination] = [.overview, .savings, .payments, .contracts, .loans, .jobs, .accounts]

    var title: String {
        switch self {
        case .overview: "Übersicht"
        case .savings: "Sparziele"
        case .payments: "Zahlungen"
        case .contracts: "Verträge"
        case .loans: "Kredite"
        case .jobs: "Jobs"
        case .accounts: "Konten"
        case .settings: "Einstellungen"
        }
    }

    var symbol: String {
        switch self {
        case .overview: "chart.xyaxis.line"
        case .savings: "target"
        case .payments: "arrow.left.arrow.right"
        case .contracts: "doc.text"
        case .loans: "creditcard"
        case .jobs: "briefcase"
        case .accounts: "building.columns"
        case .settings: "gearshape"
        }
    }
}

public struct RootView: View {
    @Environment(AppStore.self) private var store
    @Environment(\.scenePhase) private var scenePhase
    @State private var selection: Destination = .overview
    @State private var macSelection: Destination? = .overview

    public init() {}

    public var body: some View {
        Group {
            if store.session == nil {
                AuthView()
            } else {
                VStack(spacing: 0) {
                    if store.demo || store.offline { statusBanner }
                    navigation
                }
            }
        }
        .tint(KontaStyle.accent)
        .environment(\.locale, Locale(identifier: "de_DE"))
        .task {
            if store.session != nil && !store.demo { await reload() }
            await NativeNotifications.shared.restore()
            await store.registerDevice()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { Task { await reload() } }
        }
        .onReceive(NotificationCenter.default.publisher(for: NativeNotifications.refresh)) { notification in
            Task {
                await reload()
                if let id = notification.object as? String,
                   store.households.contains(where: { $0.id == id }) {
                    await store.selectHousehold(id)
                }
                selection = .overview
                macSelection = .overview
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: NativeNotifications.registered)) { _ in
            Task { await store.registerDevice() }
        }
        .onOpenURL { url in
            guard url.scheme == "konta" else { return }
            switch url.host {
            case "invitations", "verify":
                macSelection = .settings
                Task { await reload() }
            case "reset":
                store.pendingPasswordReset = true
            default:
                break
            }
        }
        .alert("Das hat nicht geklappt", isPresented: Binding(
            get: { store.error != nil },
            set: { if !$0 { store.error = nil } }
        )) {
            Button("OK") { store.error = nil }
        } message: { Text(store.error ?? "") }
        .alert("Konta", isPresented: Binding(
            get: { store.message != nil },
            set: { if !$0 { store.message = nil } }
        )) {
            Button("OK") { store.message = nil }
        } message: { Text(store.message ?? "") }
    }

    private var statusBanner: some View {
        HStack {
            Label(
                store.demo ? "Vorschau mit Beispieldaten" : "Offline · gespeicherter Stand",
                systemImage: store.demo ? "play.circle" : "wifi.slash"
            ).font(.caption)
            Spacer()
            if store.demo {
                Button("Vorschau beenden") { store.clearSession() }.font(.caption)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 8)
        .background(KontaStyle.accent.opacity(0.08))
    }

    @ViewBuilder private var navigation: some View {
        #if os(macOS)
        NavigationSplitView {
            VStack(spacing: 0) {
                if store.households.count > 1 { householdSelector }
                List(selection: $macSelection) {
                    ForEach(Destination.primary) { destination in
                        Label(destination.title, systemImage: destination.symbol)
                            .tag(destination)
                            .padding(.vertical, 5)
                    }
                }
                .listStyle(.sidebar)

                Button {
                    macSelection = .settings
                } label: {
                    Label("Einstellungen", systemImage: "gearshape")
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
                .background(macSelection == .settings ? KontaStyle.accent.opacity(0.12) : .clear)
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .padding(8)
            }
            .navigationSplitViewColumnWidth(min: 210, ideal: 235, max: 290)
        } detail: {
            NavigationStack { destination(macSelection ?? .overview) }
        }
        #else
        TabView(selection: $selection) {
            ForEach(Destination.primary) { item in
                Tab(item.title, systemImage: item.symbol, value: item) {
                    NavigationStack { destination(item) }
                }
            }
        }
        .tabBarMinimizeBehavior(.onScrollDown)
        #endif
    }

    #if os(macOS)
    private var householdSelector: some View {
        Menu {
            ForEach(store.households) { household in
                Button {
                    Task { await store.selectHousehold(household.id) }
                } label: {
                    if household.id == store.selectedHouseholdID {
                        Label(household.name, systemImage: "checkmark")
                    } else {
                        Text(household.name)
                    }
                }
            }
            Divider()
            Button("Haushalte verwalten", systemImage: "gearshape") { macSelection = .settings }
        } label: {
            HStack(spacing: 8) {
                Text(store.household?.name ?? "Haushalt wählen")
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Image(systemName: "chevron.up.chevron.down")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            .contentShape(Rectangle())
        }
        .menuStyle(.borderlessButton)
        .padding(.horizontal, 16)
        .padding(.top, 18)
        .padding(.bottom, 8)
    }
    #endif

    @ViewBuilder private func destination(_ destination: Destination) -> some View {
        Group {
            if destination == .settings {
                SettingsView()
            } else if store.snapshot == nil {
                if store.households.isEmpty {
                    ContentUnavailableView {
                        Label("Dein Geld. Dein Plan.", systemImage: "house")
                    } description: {
                        Text("Lege in den Einstellungen deinen ersten Haushalt an oder nimm eine Einladung an.")
                    } actions: {
                        #if os(macOS)
                        Button("Zu den Einstellungen") { macSelection = .settings }
                        #endif
                    }
                } else {
                    ProgressView("Haushalt wird geladen …")
                }
            } else {
                switch destination {
                case .overview: DashboardView()
                case .savings: SavingsGoalsView()
                case .payments: PaymentsView()
                case .contracts: RecurringCardsView(kind: .contract)
                case .loans: RecurringCardsView(kind: .loan)
                case .jobs: RecurringCardsView(kind: .job)
                case .accounts: RecordListView(kind: .account)
                case .settings: EmptyView()
                }
            }
        }
        .navigationTitle(destination.title)
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Button { Task { await reload() } } label: { Image(systemName: "arrow.clockwise") }
                    .help("Aktualisieren")
                    .accessibilityLabel("Aktualisieren")
                    .disabled(store.busy || store.demo)
            }
            #if os(iOS)
            ToolbarItem(placement: .topBarTrailing) {
                NavigationLink { SettingsView() } label: { Image(systemName: "gearshape") }
                    .accessibilityLabel("Einstellungen")
            }
            #endif
        }
    }

    private func reload() async {
        do { try await store.refresh() } catch { store.handle(error) }
    }
}
