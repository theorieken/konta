# AGENTS.md — Konta

The September 2026 native rewrite supersedes the former Django/Next.js guide.
The user explicitly requested a fresh project with exactly three source roots:
`ios`, `macos`, and `api`. Root documentation/configuration files are fine.

## Architecture

- German UI and documentation; English code identifiers and comments.
- iOS/iPadOS 26 and macOS 26; Swift 6, SwiftUI, Swift Charts, native navigation.
- iOS uses the system TabView and Liquid Glass. macOS is a standalone Mac app
  using NavigationSplitView, not Catalyst or a web wrapper.
- Shared models, client, finance engine and views live in the local Swift package
  `ios/KontaKit`; macOS references it. Do not duplicate the finance engine.
- CakePHP 5.4 API, PHP >=8.3. Composer lock is authoritative. SQLite defaults,
  MySQL optional. Use Cake migrations and database bindings, never concatenate
  user data into SQL. No web frontend, Django, Node, Redis or Celery.
- The API handles identities, authorization, data, uploads/classification, email
  and APNs. Projection and recurring plan generation run in Swift.
- Financial records use an allowlisted typed JSON payload in `records`, with
  household ownership, kind, optimistic version and audit fields outside it.

## Invariants

- UUID identities and household authorization for every read and write.
  Validate referenced accounts, categories and plans inside the same household.
- A household has one owner. Membership alone never allows invitation/settings/
  role administration. Invitations require verified email and explicit acceptance;
  matching a supplied email string does not grant access.
- Money is signed Int64/integer cents. Transaction income positive, expense
  negative. Recurring source amount is a positive magnitude; direction determines
  its sign in the native engine. Never use floating point to calculate balances.
- Start balances only count from their date. Earlier transactions do not count
  again. A balance named today excludes future and planned bookings.
- Virtual plans have `kind:UUID:YYYY-MM-DD` keys. A real booking's matchedPlanKey
  suppresses exactly that plan, including a manually entered one-off plan.
  One active booking per matched key is enforced by a database unique index.
- Manual categories win. Classification checks version and category ownership
  after network calls; matching may replace an automatic category with the plan's.
- CSV parsing must keep date columns out of amounts and prefer Verwendungszweck
  over Buchungstext. Import hashes are per household/account/date/amount/purpose/
  counterparty/external-ID. Invalid rows reject the entire import.
- Every write uses version checking. Do not silently overwrite conflicts.
- Data changes reload the shared snapshot; APNs and foreground refresh invalidate
  it across devices. No polling. Offline snapshots are encrypted and read-only.
- Tokens are random, hashed in the database, expiring, and stored in Apple
  Keychain on clients. No secrets in UserDefaults, source, logs, URLs or fixtures.
- Do not forward bearer credentials through redirects. Release API URLs require
  HTTPS; DEBUG permits HTTP only for loopback.
- Email and APNs use the persistent outbox with retry and claim leases. No live
  external sending in tests. Default local email writes private .eml files.
- `.env`, `.env.legacy`, signing config, `.p8`, private uploads and databases stay
  ignored. Never print or copy existing user secrets into generated source.

## UI

Use native controls, forms, sheets, document pickers, menus and notifications.
Keep one violet accent. Green/red are reserved for signed money (system
validation/destructive controls retain native semantics). Money always uses
`Money`/`Euro`, dates use `Day`, amounts use monospaced digits. Support VoiceOver,
Dynamic Type and system dark mode. Demo data must be labeled and read-only.

## Validation

- `KONTA_PHP=/path/to/php bash api/bin/test.sh`
- `KONTA_PHP=/path/to/php python3 api/tests/http_smoke.py`
- `swift test --package-path ios/KontaKit`
- Build both Xcode projects using the Konta scheme. Unsigned simulator/Mac builds
  are valid local checks; do not claim distribution signing or APNs delivery from
  them. Inspect native UI after layout changes.
- Re-run XcodeGen after project.yml edits. Keep the generated .xcodeproj files.
- Add meaningful regressions for money, authorization, identity, imports and
  concurrency. Preserve the synthetic HTTP response fixture contract with Swift.
- API deployment needs only webroot public, persistent storage, HTTPS and cron
  for `bin/cake.php maintenance`. Test migrations from an empty database.

See README.md, APPLE_SETUP.md, and api/docs/API.md for operational details.
