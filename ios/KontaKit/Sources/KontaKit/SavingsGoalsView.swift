import SwiftUI

struct SavingsGoalsView: View {
    @Environment(AppStore.self) private var store
    @State private var amount = ""
    @State private var date = Day.addingMonths(12, to: Date())

    private var balance: Int64 {
        FinanceEngine.balance(records: store.records, at: Date(), includePlanned: false)
    }
    private var target: Int64 { store.household?.savingsGoal ?? 0 }
    private var projected: Int64 {
        FinanceEngine.balance(records: store.records, at: date, includePlanned: true)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                goalCard
                if store.isOwner && !store.demo { editor }
            }
            .padding(24)
            .frame(maxWidth: 800)
            .frame(maxWidth: .infinity)
        }
        .background(KontaStyle.canvas)
        .onAppear { load() }
        .onChange(of: store.household?.id) { _, _ in load() }
    }

    private var goalCard: some View {
        VStack(alignment: .leading, spacing: 22) {
            HStack {
                Image(systemName: "target")
                    .font(.title2)
                    .foregroundStyle(KontaStyle.accent)
                Spacer()
                if target > 0 {
                    Text(progress.formatted(.percent.precision(.fractionLength(0))))
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
            }

            if target > 0 {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Euer Sparziel").font(.subheadline).foregroundStyle(.secondary)
                    Money(cents: target)
                        .font(.system(.largeTitle, design: .rounded, weight: .semibold))
                    if let goalDate = store.household?.goalDate {
                        Text("bis \(Day.label(goalDate))").foregroundStyle(.secondary)
                    }
                }

                ProgressView(value: progress)
                    .tint(KontaStyle.accent)
                    .controlSize(.large)

                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Heute").font(.caption).foregroundStyle(.secondary)
                        Money(cents: balance).font(.headline)
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("Laut Plan").font(.caption).foregroundStyle(.secondary)
                        Money(cents: projected).font(.headline)
                    }
                }

                Label(
                    projected >= target
                        ? "Mit eurem aktuellen Plan ist das Ziel erreichbar."
                        : "Zum Ziel fehlen laut Plan noch \(Euro.format(target - projected)).",
                    systemImage: projected >= target ? "checkmark.circle.fill" : "info.circle"
                )
                .font(.subheadline)
                .foregroundStyle(projected >= target ? KontaStyle.income : .secondary)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Wofür möchtet ihr sparen?")
                        .font(.system(.title, design: .rounded, weight: .semibold))
                    Text("Lege einen Betrag und ein Datum fest. Konta zeigt euch sofort, ob der aktuelle Plan dazu passt.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(26)
        .kontaCard()
    }

    private var editor: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(target > 0 ? "Ziel bearbeiten" : "Ziel anlegen").font(.headline)
            Grid(alignment: .leading, horizontalSpacing: 18, verticalSpacing: 14) {
                GridRow {
                    Text("Zielbetrag")
                    TextField("0,00 €", text: $amount)
                        .textFieldStyle(.roundedBorder)
                }
                GridRow {
                    Text("Zieldatum")
                    DatePicker("", selection: $date, in: Date()..., displayedComponents: .date)
                        .labelsHidden()
                }
            }
            Button {
                Task { await save() }
            } label: {
                Label("Sparziel speichern", systemImage: "checkmark")
            }
            .buttonStyle(.borderedProminent)
            .disabled(!store.canWrite)
        }
        .padding(22)
        .kontaCard()
    }

    private var progress: Double {
        guard target > 0 else { return 0 }
        return min(max(Double(balance) / Double(target), 0), 1)
    }

    private func load() {
        amount = Euro.input(target)
        date = store.household?.goalDate.map(Day.date) ?? Day.addingMonths(12, to: Date())
    }

    private func save() async {
        await store.perform {
            guard var household = store.household,
                  let cents = Euro.parse(amount),
                  cents >= 0 else {
                throw APIError(status: 0, message: "Bitte einen gültigen Zielbetrag eingeben.")
            }
            household.savingsGoal = cents
            household.goalDate = Day.string(date)
            try await store.updateHousehold(household)
            store.message = "Sparziel gespeichert."
        }
    }
}
