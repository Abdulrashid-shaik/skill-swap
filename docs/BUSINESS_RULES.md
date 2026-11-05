# Business Rules & State Transitions

All sensitive rules are enforced **server-side**. The frontend never decides outcomes. Entities are defined in [DATABASE_ERD.md](DATABASE_ERD.md).

## 1. Strict mutual matching (M4)

User B is a valid match for user A **iff all** hold:

- `(A.OFFER ∩ B.WANT) ≠ ∅` — A teaches something B wants, **AND**
- `(B.OFFER ∩ A.WANT) ≠ ∅` — B teaches something A wants,
- `A ≠ B`,
- neither has blocked the other,
- B is active (`is_active=True, is_deactivated=False, is_suspended=False`),
- only `APPROVED, is_active` skills count.

One-directional overlap is **not** a match. Computed on demand via ORM joins on `UserSkill(kind, is_active)` filtered to approved skills. A simple score = count of exchangeable skill pairs orders results (no AI — set intersection only).

**Re-validated server-side at request-create and at accept.** A stale frontend match can never create or accept an exchange.

## 2. ExchangeRequest state machine (M5)

```
            accept (receiver)                   → creates Exchange (atomic)
PENDING ───────────────────────────► ACCEPTED
   │  reject (receiver)  → REJECTED
   │  cancel (sender)    → CANCELLED
```

Guards:
- Only the **receiver** may accept/reject; only the **sender** may cancel.
- At most one `PENDING` per `(sender, receiver)` (partial unique constraint).
- Blocked pairs (either direction) cannot create a request.
- On accept: **re-validate mutual compatibility**; then create the `Exchange` in the same `transaction.atomic()` block as the status change.
- Terminal states (`ACCEPTED`/`REJECTED`/`CANCELLED`) are immutable.

## 3. Exchange state machine (M6)

```
ONGOING ──(dual confirmation)──► COMPLETED
   │
   └──(cancel by either participant)──► CANCELLED
```

- Exactly two participants. One agreed skill-pair (R16).
- `COMPLETED`/`CANCELLED` are terminal and not reopened via ordinary requests.
- **One ONGOING exchange per user (R15).** A user may be in at most **one** `ONGOING`
  exchange at a time, across *all* partners. Enforced for **both** participants at accept
  time, inside an atomic transaction, and guaranteed by the `OngoingExchangeParticipant`
  unique(`user`) constraint — the real backstop on SQLite, where `select_for_update` is a
  no-op. `transaction_mode=IMMEDIATE` serializes concurrent accepts so one wins cleanly and
  the other is rejected (not a deadlock). The slot is released on completion/cancellation.

## 4. Dual completion confirmation (M6 — critical)

The exchange completes only when **both** participants have independently confirmed. The first confirmation must **not** complete it.

```
POST /api/v1/exchanges/{id}/confirm/        (participant only)

with transaction.atomic():
    exchange = Exchange.objects.get(pk=id)          # re-read inside txn
    assert request.user in (participant_a, participant_b)   # else 403
    if exchange.status != ONGOING:
        return 409 Conflict                          # terminal / wrong state
    ExchangeConfirmation.objects.get_or_create(      # unique(exchange, user)
        exchange=exchange, user=request.user)
    if ExchangeConfirmation.objects.filter(exchange=exchange).count() == 2:
        exchange.status = COMPLETED
        exchange.completed_at = now()
        exchange.save(update_fields=["status", "completed_at"])
        increment completed_exchanges for both participants
        create notifications: exchange_completed (both)
    else:
        create notification: confirmation_recorded (other participant)
```

**Why it is race-safe on SQLite:** `select_for_update` is a no-op on SQLite, so correctness comes from three things together — the `transaction.atomic()` block, the in-transaction status re-check, and the `unique(exchange, user)` constraint. A racing double-confirm by the same user collapses to one row; the count is evaluated inside the transaction, so the `ONGOING → COMPLETED` transition happens exactly once. SQLite serializes writes, so these short transactions do not deadlock.

The frontend is never trusted: completion status is derived purely from confirmation rows.

## 5. ExchangeSession state machine (M8)

```
SCHEDULED ──► COMPLETED
    │   └──► CANCELLED
    └──► RESCHEDULED  (creates a new SCHEDULED session, linked via previous_session)
```

- Participants only. Timezone-aware (`USE_TZ=True`, stored UTC).
- Reschedule/cancel updates or deletes the Google event when integration is connected (P9); otherwise session remains fully usable.
- Each transition notifies both participants.

## 6. Review eligibility (M11)

A review is allowed **iff**:
- `exchange.status == COMPLETED`,
- reviewer is a participant,
- no existing review by that reviewer for that exchange (`unique(exchange, reviewer)`).

Creating a review updates the reviewee's `UserProfile.rating_avg` and `rating_count` in a transaction.

## 7. Blocking semantics (M12 — R5/R17)

- A block (`blocker → blocked`) removes both users from each other's discovery and matching results and forbids **new** requests in either direction.
- **Existing exchanges remain fully intact** — their chat and sessions continue to work. Blocking does not cancel or freeze an active exchange.
- Unblock restores discoverability and the ability to send new requests.

## 8. Notification triggers (M10)

Created on: request received/accepted/rejected/cancelled, new message, upcoming session, session rescheduled/cancelled, confirmation recorded, exchange completed, review received. Each carries a `type` + `target_url` deep link. "Upcoming session" reminders in v1 are generated at schedule time and surfaced live on the dashboard; true timed reminders depend on an approved scheduler (see R11 in [DECISIONS.md](DECISIONS.md)).

## 9. SQLite transaction discipline

Wrap every multi-row state change in `transaction.atomic()` and keep it short: request-accept (+ exchange create), exchange confirm/complete, review create (+ aggregate update), session reschedule. Enable WAL mode for read/write concurrency.

## Account suspension enforcement (M12 / R12)

Suspension is enforced at every layer — not the frontend:

- **Login:** `SuspensionAwareModelBackend` refuses authentication for a currently-suspended
  account (staff exempt, so admins keep access).
- **Existing sessions:** `SuspensionMiddleware` blocks suspended, non-staff users on every
  request with a branded **403** (JSON for `/api/`); they may still log out.
- **Services / API:** `ensure_not_suspended()` guards create/accept request and message send;
  the DRF `IsNotSuspended` permission backs the API.
- **Discovery:** suspended users are hidden; the queryset honors `suspended_until`.
- **Auto-expiry:** a `suspended_until` in the past clears lazily on the user's next
  auth/request (`lift_suspension_if_expired`) — no scheduler needed.

`is_currently_suspended` is the single source of truth: `is_suspended` is true **and** any
`suspended_until` is still in the future.

## Rate limiting

Abuse-prone endpoints are rate-limited server-side (`apps/common/ratelimit.py`), returning
**HTTP 429** with a `Retry-After` header once a fixed window is exceeded:

| Endpoint | Limit |
|---|---|
| Login | 30 / 5 min per IP **and** 8 / 5 min per email |
| Registration | 10 / hour per IP |
| Password reset | 10 / hour per IP + 5 / hour per email |
| Chat send | 30 / min per account |
| Report submit | 5 / hour per account |
| API request-create / message / report | per-account windows (same mechanism) |

Counts use an atomic `F()+1` DB update (not `cache.incr()`, which is non-atomic), so the
limiter fails **closed** under concurrency. Client IP uses `REMOTE_ADDR` unless
`RATELIMIT_TRUSTED_PROXY_COUNT > 0` (a spoofable `X-Forwarded-For` is ignored by default).
Login/password-reset responses stay uniform to avoid account enumeration.
