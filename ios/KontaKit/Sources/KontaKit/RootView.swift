import SwiftUI

public enum Destination: String, CaseIterable, Identifiable {
    case overview, expenses, income, household
    public var id: String { rawValue }
    var title: String { switch self { case .overview: "Übersicht"; case .expenses: "Ausgaben"; case .income: "Einnahmen"; case .household: "Haushalt" } }
    var symbol: String { switch self { case .overview: "chart.xyaxis.line"; case .expenses: "arrow.up.right"; case .income: "arrow.down.left"; case .household: "person.2" } }
}

public struct RootView: View {
    @Environment(AppStore.self) private var store
    @Environment(\.scenePhase) private var scenePhase
    @State private var selection: Destination = .overview
    @State private var macSelection: Destination? = .overview
    @State private var showSettings = false
    public init() {}
    public var body: some View {
        @Bindable var store = store
        Group {
            if store.session == nil { AuthView() }
            else {
                VStack(spacing: 0) {
                    if store.demo || store.offline {
                        HStack {
                            Label(store.demo ? "Vorschau mit Beispieldaten" : "Offline · gespeicherter Stand", systemImage: store.demo ? "play.circle" : "wifi.slash").font(.caption)
                            Spacer()
                            if store.demo { Button("Vorschau beenden") { store.clearSession() }.font(.caption) }
                        }.padding(.horizontal, 20).padding(.vertical, 8).background(KontaStyle.accent.opacity(0.08))
                    }
                    navigation
                }
            }
        }
        .tint(KontaStyle.accent)
        .environment(\.locale, Locale(identifier: "de_DE"))
        .task { if store.session != nil && !store.demo { await reload() }; await NativeNotifications.shared.restore(); await store.registerDevice() }
        .onChange(of: scenePhase) { _, phase in if phase == .active { Task { await reload() } } }
        .onReceive(NotificationCenter.default.publisher(for: NativeNotifications.refresh)) { notification in
            Task {
                await reload()
                if let id = notification.object as? String {
                    if store.households.contains(where: { $0.id == id }) { await store.selectHousehold(id) }
                    selection = .household; macSelection = .household
                }
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: NativeNotifications.registered)) { _ in Task { await store.registerDevice() } }
        .onOpenURL { url in
            guard url.scheme == "konta", url.host == "invitations" else { return }
            selection = .household; macSelection = .household
            Task { await reload() }
        }
        .alert("Das hat nicht geklappt", isPresented: Binding(get: { store.error != nil }, set: { if !$0 { store.error = nil } })) { Button("OK") { store.error = nil } } message: { Text(store.error ?? "") }
        .alert("Konta", isPresented: Binding(get: { store.message != nil }, set: { if !$0 { store.message = nil } })) { Button("OK") { store.message = nil } } message: { Text(store.message ?? "") }
    }
    @ViewBuilder private var navigation: some View {
        #if os(macOS)
        NavigationSplitView {
            VStack(spacing: 0) {
                HStack(spacing: 10) { KontaMark(size: 34); Text("Konta").font(.title2.weight(.bold)); Spacer() }.padding(20)
                List(selection: $macSelection) {
                    Section("Dein Geld") {
                        ForEach(Destination.allCases) { destination in Label(destination.title, systemImage: destination.symbol).tag(destination).padding(.vertical, 6) }
                    }
                }.listStyle(.sidebar)
                VStack(alignment: .leading, spacing: 12) {
                    Text(store.household?.name ?? "Deine Haushalte").font(.subheadline.weight(.medium))
                    Button { showSettings = true } label: { Label("Einstellungen", systemImage: "gearshape") }.buttonStyle(.plain)
                }.padding(20).frame(maxWidth: .infinity, alignment: .leading)
            }.navigationSplitViewColumnWidth(min: 210, ideal: 235, max: 290)
        } detail: {
            NavigationStack { destination(macSelection ?? .overview) }
        }.sheet(isPresented: $showSettings) { NavigationStack { SettingsView() }.frame(minWidth: 620, minHeight: 650) }
        #else
        TabView(selection: $selection) {
            ForEach(Destination.allCases) { item in
                Tab(item.title, systemImage: item.symbol, value: item) { NavigationStack { destination(item) } }
            }
        }.tabBarMinimizeBehavior(.onScrollDown)
        #endif
    }
    @ViewBuilder private func destination(_ destination: Destination) -> some View {
        Group {
            if destination == .household { HouseholdView() }
            else if store.snapshot == nil {
                if store.households.isEmpty { ContentUnavailableView { Label("Dein Geld. Euer Plan.", systemImage: "house") } description: { Text("Lege im Bereich Haushalt deinen ersten Haushalt an oder nimm eine Einladung an.") } }
                else { ProgressView("Haushalt wird geladen …") }
            } else {
                switch destination {
                case .overview: DashboardView()
                case .expenses: TransactionsView(income: false)
                case .income: TransactionsView(income: true)
                case .household: EmptyView()
                }
            }
        }.navigationTitle(destination.title)
            .toolbar {
                ToolbarItem(placement: .automatic) {
                    Button { Task { await reload() } } label: { Image(systemName: "arrow.clockwise") }.help("Aktualisieren").accessibilityLabel("Aktualisieren").disabled(store.busy || store.demo)
                }
            }
    }
    private func reload() async { do { try await store.refresh() } catch { store.handle(error) } }
}
