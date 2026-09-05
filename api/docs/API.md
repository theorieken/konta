# Konta API contract

Base URL: server root; API prefix `/v1`. JSON request and response bodies, except multipart CSV uploads and authenticated file downloads. No cookies, web sessions or browser frontend. Errors always return JSON with `detail`. HTTP 401 means reauthentication; 403 means no household/role access; 404 covers missing/foreign records; 409 means a version, relationship or invitation conflict; 422 means validation failure; 429 means rate limiting.

Authorization: `Authorization: Bearer <token>`. Sessions last 30 days. Only SHA-256 token hashes are stored. Verification/reset codes expire in one hour and are single use. Invitation acceptance requires a verified account with the exact normalized target email.

## Endpoints

| Method | Path | Body / result |
|---|---|---|
| GET | `/health` | Database connectivity, service status |
| POST | `/v1/auth/register` | `name`, `email`, `password`; returns `{token,user}` |
| POST | `/v1/auth/login` | `email`, `password`; returns `{token,user}` |
| POST | `/v1/auth/forgot` | `email`; generic success, code via email |
| POST | `/v1/auth/reset` | `code`, `password`; revokes all sessions/devices |
| POST | `/v1/auth/verify` | `code` |
| POST | `/v1/auth/resend` | Empty object; authenticated verification email |
| POST | `/v1/auth/logout` | Optional `deviceToken`; revokes current session/device |
| GET | `/v1/bootstrap` | `{user,households,invitations,notifications}` |
| PATCH | `/v1/me` | `name`; returns user |
| DELETE | `/v1/me` | `password`; owner must transfer/delete households first |
| POST/DELETE | `/v1/devices` | `token`; POST also `platform:ios|macos`, `environment:development|production` |
| POST | `/v1/notifications/{id}` | Mark own notification read |
| POST | `/v1/households` | `name`; creates household and 23 reference categories |
| PATCH | `/v1/households/{h}` | Household settings plus current `version`; owner only |
| DELETE | `/v1/households/{h}` | `confirmation` equal to household name; owner only |
| GET | `/v1/households/{h}/snapshot` | `{household,records,members,uploads,invitations}` |
| POST | `/v1/households/{h}/invitations` | `email`; owner and verified account required |
| DELETE | `/v1/households/{h}/invitations/{id}` | Revoke pending invitation; owner |
| POST | `/v1/invitations/{id}` | `accept:boolean`; verified recipient only |
| DELETE | `/v1/households/{h}/members/{user}` | Owner removes member, or member leaves |
| POST | `/v1/households/{h}/transfer` | `userID`; transfers sole ownership to existing member |
| PUT | `/v1/households/{h}/records/{kind}/{id}` | FinanceRecord, `version:0` on create, current version on update |
| DELETE | `/v1/households/{h}/records/{id}` | `version`; soft delete, referenced accounts/categories protected |
| POST | `/v1/households/{h}/uploads` | Multipart `accountID`, `file`; CSV up to 10 MB/2,000 bookings |
| GET | `/v1/households/{h}/uploads/{id}` | Private original CSV download |
| POST | `/v1/households/{h}/classify` | `ids:[UUID]`, max 25; opt-in and server OpenAI key required |

Household financial data is available to members; pending sent invitations are included only for the owner. Bootstrap invitation metadata is hidden until the user's email is verified. A successful mutation generally reloads the snapshot in the native clients; writes emit silent APNs invalidations via the outbox.

## FinanceRecord

Swift's `FinanceRecord` in `ios/KontaKit/Sources/KontaKit/Models.swift` and PHP's `Records::defaults()` define the wire schema. All responses include the default fields, so Swift can decode a single concrete value type without per-model adapters. `id`, `kind`, `version`, `createdAt`, `updatedAt` are supplied by the record envelope. Account/category relationships are required for transactions and recurring sources and validated against the household.

`kind` is one of `account`, `category`, `transaction`, `contract`, `loan`, `job`. Account `amount` is the opening balance in integer cents; transaction `amount` is signed integer cents; recurring `amount` is a positive magnitude. `principal` is loan outstanding balance at `date`. `interestBasisPoints` is hundredths of a percentage point (1200 = 12%). Supported recurrence values: once, weekly, biweekly, monthly, quarterly, semiannual, yearly. Dates use `YYYY-MM-DD`, interpreted as civil dates in Europe/Berlin by the clients.

`matchedPlanKey` is `kind:UUID:YYYY-MM-DD`, held only by a real transaction. It points to the source and occurrence, including a planned one-off. A unique index prevents two active bookings from suppressing the same occurrence. Soft deletion releases the match while retaining the record payload for audit. Deleting a recurring source does not delete its real bookings.

Manual edits may set category ownership to `manual`; the API controls classification confidence and import hash. Imported rows start with keyword classification and `needsReview` below 0.6. Optional AI can update automatic/unmatched records only and rechecks their versions after network calls. It uses the [OpenAI Responses API with Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), a fixed endpoint, allowlisted category IDs and `store:false`.

## Deployment boundaries

Local storage is private under `storage/uploads`; filenames on disk are server UUIDs. SQLite foreign keys, WAL and busy timeout are explicitly enabled. MySQL uses equivalent migrations. Financial relationships are validated while serializing writes within the household; optimistic record versions prevent lost updates. The default installation uses one API process/host with private local storage.

The maintenance command handles outbox delivery retries, expired tokens, rate-limit buckets, successful outbox retention and soft-deleted financial rows older than 90 days. Financial projections need no backend cron: both native apps compute them on demand.
