# AGENTS.md — Haushalts-Finanzplanung

Guide for anyone (human or agent) working on this repository. Read this before
touching code. It records both **what was asked for** and **the conventions the
existing code already follows** — deviating from them is how this codebase gets
worse.

---

## 1. What this is

A self-hosted financial planning app for a **single household**. It answers one
question well: *given what we earn, what we owe and what we spend, how much money
will we have in month N — and will we hit our savings goal?*

The domain reference is [`reference.xlsx`](reference.xlsx) in the repository root:
the spreadsheet this app replaces. It defines the vocabulary (Konten, monatliche
Posten, Einmalzahlungen, Sparziel, Planungshorizont) and the expense categories.
Read it when a domain question comes up.

**The UI language is German. Code, comments, commit messages and this file are
English.** Do not mix them.

---

## 2. Stack

| Layer | Choice |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Realtime | Django Channels (ASGI, daphne) over Redis |
| Async work | Celery + Celery Beat (`django-celery-beat`, DB scheduler) |
| Database | PostgreSQL 16 |
| Object storage | MinIO (S3 API via `django-storages`) |
| Cache / broker | Redis 7 |
| AI | OpenAI SDK, model selectable in the settings UI |
| Frontend | Next.js 15 (App Router) + React 19 |
| State | Redux Toolkit + RTK Query |
| UI kit | Material UI 6 |
| Charts | Recharts |
| Reverse proxy | nginx — one host port for the entire stack |

---

## 3. Repository layout

```
.
├── deploy.sh                 one command to build + run everything
├── docker-compose.yml
├── .env.example              every value has a working default
├── docker/nginx/             single entry point: /api /ws /admin /static /s3 /
├── reference.xlsx            the spreadsheet this app replaces
├── backend/
│   ├── config/               settings, urls, asgi, celery
│   ├── base/                 ← the "hot" shared layer (see §5)
│   ├── users/                User
│   ├── finance/              Account, Category, Transaction, Contract, Loan, Job
│   └── imports/              CSV parsing + AI classification (no models)
└── frontend/
    ├── src/app/              routes only, thin
    │   ├── login/  onboarding/
    │   └── (app)/            everything behind the AppShell
    └── src/base/             ← the "hot" shared layer (see §6)
```

**Rule:** `base/` on both sides holds anything shared across features. If a
second feature needs it, it moves to `base/`. If only one page needs it, it stays
next to that page.

---

## 4. Data model

Ten models, no more. Adding an eleventh needs a real reason.

| Model | App | Purpose |
|---|---|---|
| `User` | users | Login; email is the username |
| `Account` | finance | A bank account, card or cash pot |
| `Category` | finance | Exactly one per transaction — the basis of every report |
| `Transaction` | finance | One money movement, past or future |
| `Contract` | finance | Something recurring that costs money |
| `Loan` | finance | Borrowed money repaid in instalments |
| `Job` | finance | A recurring income |
| `File` | base | An upload in MinIO (also tracks CSV import progress) |
| `Tag` | base | A label attachable to *anything* |
| `Setting` | base | Household key/value configuration |

### 4.1 BaseModel — every model inherits it

`backend/base/models.py`. Non-negotiable invariants:

- **UUID primary key** everywhere (`id`, `default=uuid4`, not editable).
- **`name`** — a human readable label. Never empty in the API: `display_name`
  falls back to `"{verbose_name} {short-id}"`.
- **`created_at` / `updated_at`** — audit timestamps.
- **`created_by`** — FK to the user, nullable, `SET_NULL`. Set automatically by
  `BaseSerializer.create()`; do not set it by hand in views.
- **`notes`** — free text, always available.
- **Soft delete** via `deleted_at`. `Model.objects` hides deleted rows,
  `Model.all_objects` does not. `instance.delete()` soft-deletes;
  `instance.delete(hard=True)` really deletes. A weekly Celery task purges rows
  soft-deleted more than 90 days ago.
- **`object_reference`** → `"{db_table}-{uuid}"`. This is *the* addressing scheme
  of the whole system.

### 4.2 Object references

`finance_transaction-1b2c3d4e-....` — table name, a dash, a UUID.

Parsed by anchoring on the trailing 36 characters, **never** by splitting on `-`
(table names contain underscores, UUIDs contain dashes). Both sides implement the
same rule: `backend/base/registry.py::split_reference` and
`frontend/src/base/lib/reference.ts::parseReference`. Change one, change both.

Everything downstream depends on it:
- `GET/PATCH/DELETE /api/objects/{reference}/` — generic access to any object
- `/objects/{reference}` — the generic frontend page
- the object drawer
- tags (`db_table` + `object_uuid`)
- `Transaction.origin_reference`

### 4.3 Transactions — the two rules that matter

1. **`amount` is signed.** Income positive, expense negative. Every balance is
   then a plain `SUM` and no report needs a case distinction. Forms show a
   positive amount plus a `direction` field; `TransactionSerializer.validate`
   converts. Never store an unsigned amount.
2. **`state` is `reality` or `planned`.** `reality` happened. `planned` is the
   projection. Planned rows are generated from Contracts/Loans/Jobs, or entered
   by hand for one-offs.

### 4.4 Superseded plans — read this before touching any total

When an imported booking matches a planned transaction, the planned row is
**kept** (audit trail) with `matched_transaction` set, and is then excluded from
every list and every total. Otherwise rent would be counted twice in the month it
was both planned and paid.

One rule, implemented in two places that must stay in sync:
- `finance/services/projection.py::counted_transactions()` (dashboard)
- `finance/views.py::TransactionViewSet.get_queryset()` (lists + summary)

Opt out with `?include_superseded=true`. Fetching a single object always works.

---

## 5. Backend conventions

### 5.1 The `base` app

| Module | Responsibility |
|---|---|
| `models.py` | `BaseModel`, `Tag`, `Setting`, `File` |
| `serializers.py` | `BaseSerializer` (the `_meta` block), serializer registry |
| `views.py` | `BaseViewSet`, generic object endpoints, health |
| `registry.py` | `db_table` → model, reference parsing |
| `settings_registry.py` | Typed definitions of every setting |
| `authentication.py` | `ExpiringTokenAuthentication` |
| `events.py` | WebSocket broadcast helpers |
| `queue.py` | `enqueue()` — the only way to dispatch a Celery task |
| `middleware.py` / `consumers.py` / `routing.py` | Channels |
| `exceptions.py` | Uniform `{detail, errors}` error envelope |
| `pagination.py`, `permissions.py` | Self-explanatory |

### 5.2 `_meta` — the standard serialization envelope

Every serializer inherits `BaseSerializer` and therefore emits:

```json
"_meta": {
  "id": "…", "object_reference": "finance_transaction-…",
  "db_table": "finance_transaction", "model": "finance.transaction",
  "verbose_name": "Transaktion", "verbose_name_plural": "Transaktionen",
  "name": "Miete Wohnung",
  "created_at": "…", "updated_at": "…", "deleted_at": null, "is_deleted": false,
  "created_by": {"id": "…", "name": "Theo", "object_reference": "users_user-…"},
  "tags": [{"id": "…", "name": "fix", "color": "#8ab", …}],
  "api_url": "/api/objects/…/", "frontend_url": "/objects/…"
}
```

**Never strip `_meta` from a response.** The drawer, the generic object page and
tag rendering all read it.

New serializer checklist:
1. Inherit `BaseSerializer`.
2. `fields = BaseSerializer.BASE_FIELDS + (...)`.
3. `read_only_fields = BaseSerializer.BASE_READ_ONLY_FIELDS + (...)`.
4. Decorate with `@register_serializer` so `/api/objects/` can resolve it.

### 5.3 Views

Inherit `BaseViewSet`. It gives you consistent permissions, `created_by`, soft
delete, tag sub-endpoints, **prefetched tags** (`build_tag_map` — do not
reintroduce an N+1) and a WebSocket broadcast on every mutation.

Recurring sources (Contract/Loan/Job) inherit `RecurringViewSet`, which rebuilds
their future planned transactions whenever the source changes.

### 5.4 Async work

**Always dispatch through `base.queue.enqueue(task, *args)`**, never
`task.delay()` directly. `enqueue` falls back to running the task inline when the
broker is unreachable and never raises — an upload must not 500 because Redis
blinked.

Beat schedule lives in `base/management/commands/setup_periodic_tasks.py` and is
re-applied on every backend start:

| Task | When | What |
|---|---|---|
| `finance.generate_planned_transactions` | daily 03:10 | Materialise sources up to the horizon |
| `finance.match_transactions` | daily 03:40 | Link bookings to the plan |
| `finance.flag_overdue_planned` | daily 04:00 | Flag plans that never happened |
| `imports.cleanup_stale_imports` | hourly | Fail imports stuck > 6 h |
| `base.prune_expired_tokens` | daily 02:30 | Token hygiene |
| `base.purge_soft_deleted` | Sundays 02:00 | Empty the bin (90 days) |

### 5.5 Plan generation

`finance/services/generator.py`. Each generated transaction carries a
`recurrence_key` (`{db_table}:{pk}:{iso-date}`) with a unique constraint, so
**generation is idempotent** — running it twice creates nothing.

- Generation starts at the **first day of the current month** and runs to the
  prediction horizon (`prediction_horizon_months`, default 24).
- `clear_future_planned()` only removes rows that are still `GENERATED`,
  `PLANNED` and unmatched. Anything a user touched or a booking matched survives.
- `resync_source()` = clear + regenerate. Called on every source edit.

### 5.6 CSV import + AI classification

Pipeline (`imports/`):

```
upload → import_transactions_from_file   parse CSV, create bookings, dedupe
           └→ classify_transactions      one Celery task per batch (default 25)
                └→ match_transaction     link each booking to its plan
```

- **Parser** (`services/csv_parser.py`) is deliberately bank-agnostic: it sniffs
  encoding and delimiter, skips preamble rows, and maps columns by *scored fuzzy
  matching* of header names. Exact match beats prefix beats substring, and within
  one field an earlier hint wins — that is what makes `Verwendungszweck` outrank
  `Buchungstext`. Money columns can never be claimed by a date column.
  Handles `1.234,56`, `-1234.56`, `(123,45)` and separate Soll/Haben columns.
  **When you add a bank format, add a hint — do not add a per-bank branch.**
- **Deduplication** via `import_hash` = SHA-256 of
  account + date + amount + counterparty + purpose + external id, with a unique
  constraint per account. Re-importing an overlapping export is safe.
- **Classifier** (`services/classifier.py`) sends a batch of transactions plus the
  category catalogue to OpenAI and asks for JSON. **Everything the model does not
  answer for falls back to keyword matching against `Category.keywords`.** That
  fallback is why the app works fully without an API key — do not remove it.
- Confidence below 0.6 sets `needs_review`.

### 5.7 Category ownership — who may overwrite whom

1. A category the **user** set is final. Any manual change clears
   `classified_by_ai`, `classification_confidence` and `classification_note`;
   `Transaction.is_auto_categorised` then returns `False` and nothing overwrites
   it again.
2. A **generated plan** beats an automatic guess: on match, the booking inherits
   the contract's category.
3. The **classifier** may only write where 1 and 2 do not apply.

### 5.8 Settings

Add a setting by adding **one** `SettingDefinition` to
`base/settings_registry.py`. The API (`/api/settings/definitions/`), the seed
command and the frontend settings page all read from there — no frontend change
needed.

Read with `Setting.get(key)` (DB → registry default → Django settings). Never
read the `Setting` model directly. Secrets (`is_secret=True`) are never returned
by the API — only whether they are set — and an empty submitted value never
overwrites a stored secret.

### 5.9 Auth

Token based, `Authorization: Token <key>`. Tokens expire after
`AUTH_TOKEN_TTL_DAYS` (0 disables). WebSockets take the token as `?token=` since
browsers cannot set headers on the handshake.

Everyone logged in belongs to the same household and may read and write
everything (`IsAuthenticatedHousehold`). `created_by` is an audit trail, **not**
an access boundary. That is deliberate — do not build per-user filtering into
this app without a product decision.

`/api/auth/onboarding/` creates the first user and refuses once one exists.

---

## 6. Frontend conventions

### 6.1 `src/base` — the "hot" layer

| Folder | Contents |
|---|---|
| `api/` | `client.ts` — token storage, fetch wrapper, error formatting |
| `store/` | `api.ts` (RTK Query), `authSlice`, `uiSlice`, typed hooks |
| `components/` | Shared UI + the whole object system |
| `components/objects/` | Drawer, display, form, field renderers, registry |
| `components/objects/models/` | **One display + one form file per model** |
| `hooks/` | `use-live-events`, `use-object-drawer`, `use-debounced` |
| `lib/` | `format.ts`, `reference.ts`, `theme.ts`, `icons.tsx` |
| `types.ts` | Mirrors the backend serializers |

### 6.2 The object system

Every model has exactly two components:

```
models/transaction-display.tsx    export function TransactionDisplay({ object })
models/transaction-form.tsx       export function TransactionForm({ object, defaults, … })
```

They are wired up in `components/objects/registry.tsx` (`db_table` → components,
label, endpoint). **Adding a model means: add the two files, add one registry
entry.** Nothing else.

- `<ObjectDisplay object={…} />` dispatches by `_meta.db_table`, falls back to a
  raw key/value list, and appends tags plus the audit footer.
- `<ObjectForm object|dbTable … />` dispatches to the model's form.
- `<ObjectDrawer />` (mounted once in the AppShell) renders the right-hand
  drawer: **object name top left, model label under it; edit / delete / maximise
  / close top right.** Maximise navigates to `/objects/{reference}`, which
  renders *the same* `ObjectDisplay`. The drawer must never be a lesser version
  of the page.
- Opening is always `useObjectDrawer().open(reference)`. Never navigate away from
  a list to look at a row.

Forms are declarative: a model form is a `FieldDef[]` plus a `save` callback
handed to `<ModelForm>`. `ModelForm` owns state, API field errors and the
buttons. Reach for a custom form only when a field genuinely cannot be described
by `FieldDef`.

### 6.3 Data access

All server state goes through **RTK Query** in `src/base/store/api.ts`. No
`fetch` in components (the one exception is the multipart CSV upload, which uses
`apiFetch`).

Cache invalidation is tag based, and a mutation must invalidate **every** view it
affects — a transaction change also invalidates `Dashboard` and `Account`. A
number must never be fresh on one screen and stale on another.

### 6.4 Live updates

One WebSocket for the whole app (`use-live-events.ts`), opened by the AppShell.
Background work (import, classification, plan generation) reports through it and
the hook invalidates the matching RTK Query tags. **Do not poll.** Reconnects
with capped exponential backoff.

### 6.5 Design rules

The brief was *minimal and clean*. Concretely:

- **Say less.** `+ Transaktion`, not `+ Transaktion hinzufügen` — the plus icon
  already says "add". Same for `+ Konto`, `+ Kategorie`, `CSV`.
- **Icons extend text, they do not replace it** (except in icon buttons, which
  always get a tooltip).
- **Show only what is needed.** An empty optional field is omitted from a display,
  not rendered as `—`.
- **One accent colour.** Green means money in, red means money out, and *nothing
  else in the app may use those two colours.* All money goes through `<Money>`.
- **Numbers use `className="tabular"`** so columns line up.
- **Cards are outlined, never shadowed.** Hairline dividers over boxes.
- **German formatting throughout** via `lib/format.ts`. Never call
  `toLocaleString` in a component.
- Layout is **sidebar left, content right**. Below `md` the sidebar becomes a
  temporary drawer behind a hamburger.
- Charts: `isAnimationActive={false}` everywhere. A chart rendered in a
  background tab never finishes its entry animation and stays blank.
- Do not put `height: 100%` on `html`/`body`. It silently breaks the sticky
  sidebar. (It has already been done once. Do not do it again.)

### 6.6 Pages

| Route | Purpose |
|---|---|
| `/onboarding` | First run: user, household, accounts. Only while no user exists. |
| `/login` | Token login |
| `/dashboard` | Projection, KPIs, category breakdown, accounts. `heute` is always marked. |
| `/expenses` | Expense transactions, contracts, loans |
| `/income` | Jobs and one-off income |
| `/objects/[reference]` | Generic object page |
| `/settings` | CSV import, AI, planning, master data, profile |

Pages are thin: they compose `base/` components and own only their local filter
state. Business logic lives in `base/` or on the server.

Dashboard `from`/`until` live in `uiSlice` so the range survives navigation, and
`/expenses` and `/income` filter by the same range.

---

## 7. Deployment

`bash deploy.sh` must **always** produce a working platform. It:

1. checks Docker,
2. creates `.env` from `.env.example` if missing, and backfills keys added by
   newer versions into an existing `.env`,
3. replaces `CHANGE_ME` secrets with generated ones,
4. **picks the next free port** if the configured one is taken, and writes it
   back to `.env`,
5. builds, starts, waits for health,
6. prints the URLs.

Other entry points: `--rebuild`, `--logs`, `--down`, `--reset`.

The backend entrypoint runs `migrate`, `collectstatic`, `seed_defaults` and
`setup_periodic_tasks` on every start. All four are idempotent — **keep them
that way**, they run on every single boot.

**The stack occupies exactly one host port.** MinIO is reachable through nginx at
`/s3/`; that location forwards `Host: minio:9000` because presigned URLs are
signed for the internal host. Do not add host port bindings to compose.

`.env` rules: every variable needs a working default, and the defaults must
describe a functioning localhost installation. A missing `.env` is not an error.

---

## 8. Working on this repo

### Definition of done
- Backend: `python manage.py check` clean, migrations generated **and committed**.
- Frontend: `npx tsc --noEmit` clean and `npx next build` succeeds.
- Anything touching money: verified against real data, not just types.
- New settings: added to `settings_registry.py`, nothing else.
- New models: `BaseModel`, registered serializer, display + form + registry entry.

### Things that have already gone wrong here
Fixed once; do not reintroduce.

1. `Wertstellung` being picked as the amount column — fuzzy header scoring must
   keep date columns away from money fields.
2. `Buchungstext` outranking `Verwendungszweck` — hint order carries weight.
3. The classifier overwriting a user's manual category — see §5.7.
4. Lists double-counting a matched plan and its booking — see §4.4.
5. `Account.balance_today` summing the entire future plan because the date bound
   was omitted. Any field called `…_today` must be bounded by today.
6. `html, body { height: 100% }` breaking the sticky sidebar.
7. Recharts bars invisible because the entry animation never runs in a hidden
   tab.
8. Publishing MinIO on host ports 9000/9001, which collide with other software.

### Style
- Python: type hints, `from __future__ import annotations`, docstrings that
  explain *why*. Business logic goes in `services/`, not in views.
- TypeScript: `strict`, no `any` outside the registry's deliberate escape hatch.
  Named exports.
- Comments explain decisions and trade-offs, not syntax.
- German user-facing strings, English identifiers. Always.
