import SwiftUI

enum KontaStyle {
    static let accent = Color(red: 0.02, green: 0.42, blue: 0.95)
    static let income = Color(red: 0.10, green: 0.48, blue: 0.34)
    static let expense = Color(red: 0.76, green: 0.27, blue: 0.28)
    #if os(macOS)
    static let canvas = Color(nsColor: .windowBackgroundColor)
    #else
    static let canvas = Color(uiColor: .systemGroupedBackground)
    #endif
}
struct Money: View {
    var cents: Int64
    var colored = false
    var body: some View {
        Text(Euro.format(cents)).monospacedDigit()
            .foregroundStyle(colored ? (cents >= 0 ? KontaStyle.income : KontaStyle.expense) : .primary)
    }
}
private struct KontaCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(.quaternary, lineWidth: 1)
            }
    }
}
extension View {
    func kontaCard() -> some View { modifier(KontaCardModifier()) }
}
struct Panel<Content: View>: View {
    var title: String
    @ViewBuilder var content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(title).font(.headline)
            content
        }.padding(22).frame(maxWidth: .infinity, alignment: .leading)
            .kontaCard()
    }
}
struct RecordRow: View {
    let record: FinanceRecord
    var subtitle: String?
    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: record.kind.symbol).font(.system(size: 18)).foregroundStyle(KontaStyle.accent)
                .frame(width: 42, height: 42).background(KontaStyle.accent.opacity(0.08), in: RoundedRectangle(cornerRadius: 13))
            VStack(alignment: .leading, spacing: 4) {
                Text(record.name).font(.body.weight(.medium)).lineLimit(2)
                if let subtitle { Text(subtitle).font(.caption).foregroundStyle(.secondary) }
            }
            Spacer(minLength: 8)
            if record.kind != .category {
                Money(cents: record.kind.isRecurring ? (record.direction == "income" ? abs(record.amount) : -abs(record.amount)) : record.amount, colored: record.kind != .account)
                    .font(.body.weight(.medium))
            }
            if record.needsReview { Image(systemName: "sparkles").foregroundStyle(KontaStyle.accent).accessibilityLabel("Zu prüfen") }
        }.padding(.vertical, 5).contentShape(Rectangle())
    }
}
struct BusyButton: View {
    var title: String
    var systemImage: String? = nil
    var action: () async -> Void
    @Environment(AppStore.self) private var store
    var body: some View {
        Button { Task { await action() } } label: {
            if let systemImage { Label(title, systemImage: systemImage) } else { Text(title) }
        }.disabled(store.busy)
    }
}
