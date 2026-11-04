# Database ERD

15 core entities. All models inherit `common.TimeStampedModel` (`created_at`, `updated_at`, auto, indexed where filtered). Primary keys are implicit `BigAutoField` unless noted. SQLite is the only database — see [BUSINESS_RULES.md](BUSINESS_RULES.md) for the concurrency approach and the dual-confirmation algorithm.

This document incorporates the Phase-0 refinements **D-1…D-5** (email login, skill approval, suspension, deactivated/suspended exclusion, timezone-aware scheduling).

## Relationship map

```
User 1─1 UserProfile
User 1─N UserSkill N─1 Skill N─1 SkillCategory
Skill N─0..1 User (suggested_by)
User 1─N ExchangeRequest (sender) / 1─N ExchangeRequest (receiver)
ExchangeRequest 1─0..1 Exchange
Exchange 1─N ExchangeConfirmation N─1 User          (max 2 confirmations)
Exchange 1─N Message N─1 User (sender)
Exchange 1─N ExchangeSession (self-FK previous_session)
Exchange 1─N Review N─1 User (reviewer) / N─1 User (reviewee)
User 1─N Notification
User 1─N UserBlock (blocker) / 1─N UserBlock (blocked)
User 1─N UserReport (reporter) / 1─N UserReport (reported)
User 1─1 GoogleCalendarConnection
```

## Entities

### User (`accounts`, extends `AbstractUser` via custom manager)
| Field | Type | Notes |
|---|---|---|
| email | Email | **unique, indexed**, `USERNAME_FIELD` |
| username | Char, null/blank | optional display handle |
| password | (Django) | PBKDF2 |
| is_active | bool | Django default |
| is_staff | bool | admin access |
| is_deactivated | bool, default F | self-service deactivation |
| deactivated_at | DateTime, null | |
| is_suspended | bool, default F | moderation action (D-3) |
| suspended_until | DateTime, null | optional auto-expiry (manual unsuspend always works; see R12) |
| date_joined | DateTime | member-since source |

- **Manager:** custom `UserManager` (email-based `create_user`/`create_superuser`).
- **Delete:** users are **deactivated/suspended, not deleted**; content FKs use PROTECT/SET_NULL to preserve history.
- **Excluded from discovery/login when:** `is_active=False` or `is_deactivated=True` or `is_suspended=True`.

### UserProfile (`accounts`) — 1-1 User (CASCADE)
| Field | Type | Notes |
|---|---|---|
| user | OneToOne(User) | CASCADE |
| full_name | Char | |
| avatar | Image → `media/avatars/`, null | validated (type/size/re-encode); needs Pillow (R14) |
| bio | Text, blank | |
| location | Char, blank | |
| experience_level | Char choices | beginner/intermediate/advanced/expert |
| rating_avg | Decimal, default 0 | denormalized cache, 0–5 |
| rating_count | int, default 0 | |
| completed_exchanges | int, default 0 | denormalized cache |

- Created via `post_save` signal on User.

### SkillCategory (`skills`)
| Field | Type | Notes |
|---|---|---|
| name | Char | **unique** |
| slug | Slug | **unique, indexed** |
| description | Text, blank | |

- **Delete:** PROTECT from `Skill` (cannot delete a category with skills).

### Skill (`skills`) — N-1 SkillCategory (PROTECT)
| Field | Type | Notes |
|---|---|---|
| name | Char | |
| slug | Slug | **unique, indexed** |
| category | FK(SkillCategory) | PROTECT |
| description | Text, blank | |
| status | Char choices | `PENDING`/`APPROVED`/`REJECTED` (D-2, R13) |
| suggested_by | FK(User), null | SET_NULL |
| is_active | bool, default T | |

- **Constraint:** `unique(name, category)` → canonical, no duplicates.
- **Index:** `(status, is_active)`.
- **Discovery/matching use `status=APPROVED, is_active=True` only.**

### UserSkill (`skills`) — N-1 User (CASCADE), N-1 Skill (PROTECT)
| Field | Type | Notes |
|---|---|---|
| user | FK(User) | CASCADE |
| skill | FK(Skill) | PROTECT |
| kind | Char choices | `OFFER` / `WANT` |
| proficiency | Char choices, null | meaningful for OFFER |
| note | Text, blank | description / learning goal |
| is_active | bool, default T | |

- **Constraint:** `unique(user, skill, kind)`.
- **Index:** `(skill, kind, is_active)` — matching hot path.

### ExchangeRequest (`exchanges`) — sender/receiver FK User (PROTECT)
| Field | Type | Notes |
|---|---|---|
| sender | FK(User) | PROTECT |
| receiver | FK(User) | PROTECT |
| offered_skill | FK(Skill) | what sender teaches |
| requested_skill | FK(Skill) | what sender learns |
| message | Text | intro message |
| status | Char choices | `PENDING`/`ACCEPTED`/`REJECTED`/`CANCELLED` |
| responded_at | DateTime, null | |

- **Constraints:** partial unique → ≤1 `PENDING` per `(sender, receiver)`; check `sender != receiver`.
- **Index:** `(receiver, status)`, `(sender, status)`.

### Exchange (`exchanges`) — 1-1 ExchangeRequest (PROTECT)
| Field | Type | Notes |
|---|---|---|
| request | OneToOne(ExchangeRequest) | PROTECT |
| participant_a | FK(User) | PROTECT |
| participant_b | FK(User) | PROTECT |
| skill_a_teaches | FK(Skill) | PROTECT |
| skill_b_teaches | FK(Skill) | PROTECT |
| status | Char choices | `ONGOING`/`COMPLETED`/`CANCELLED` |
| started_at | DateTime | |
| completed_at | DateTime, null | |
| cancelled_at | DateTime, null | |
| cancelled_by | FK(User), null | SET_NULL |
| progress_note | Text, blank | |

- Exactly two participants (model shape). One agreed skill-pair per exchange (R16).
- Guard against >1 concurrent `ONGOING` for the same participant pair + skill pair (R15).

### ExchangeConfirmation (`exchanges`) — N-1 Exchange (CASCADE), N-1 User (PROTECT)
| Field | Type | Notes |
|---|---|---|
| exchange | FK(Exchange) | CASCADE |
| user | FK(User) | PROTECT |
| confirmed_at | DateTime | auto |

- **Constraint:** `unique(exchange, user)` → one confirmation per participant.
- **Two rows → COMPLETED**, derived inside a transaction. First row never completes. See BUSINESS_RULES.

### Message (`messaging`) — N-1 Exchange (CASCADE), N-1 User sender (PROTECT)
| Field | Type | Notes |
|---|---|---|
| exchange | FK(Exchange) | CASCADE |
| sender | FK(User) | PROTECT |
| body | Text | |
| is_read | bool, default F | |
| read_at | DateTime, null | |

- **Index:** `(exchange, created_at)`, `(exchange, is_read)`.
- **Access:** exchange participants only.

### ExchangeSession (`scheduling`) — N-1 Exchange (CASCADE)
| Field | Type | Notes |
|---|---|---|
| exchange | FK(Exchange) | CASCADE |
| created_by | FK(User) | PROTECT |
| title | Char | |
| description | Text, blank | |
| scheduled_start | DateTime | **tz-aware (UTC stored)** |
| scheduled_end | DateTime | tz-aware |
| status | Char choices | `SCHEDULED`/`COMPLETED`/`CANCELLED`/`RESCHEDULED` |
| previous_session | self-FK, null | SET_NULL (reschedule chain) |
| google_event_id | Char, null | P9 |
| google_meet_link | URL, null | P9 |
| google_sync_status | Char choices | `NONE`/`PENDING`/`SYNCED`/`FAILED` |

- **Index:** `(exchange, scheduled_start)`.

### GoogleCalendarConnection (`integrations`) — 1-1 User (CASCADE)
| Field | Type | Notes |
|---|---|---|
| user | OneToOne(User) | CASCADE |
| google_account_email | Email | |
| access_token | Text | **encrypted at rest**; never serialized/logged |
| refresh_token | Text | **encrypted at rest** |
| token_expiry | DateTime | |
| scopes | Text | min scopes |
| connected_at | DateTime | |
| is_revoked | bool, default F | |

- Encryption approach pending approval (R6). Tokens excluded from all serializers/logs/templates.

### Notification (`notifications`) — N-1 User recipient (CASCADE)
| Field | Type | Notes |
|---|---|---|
| recipient | FK(User) | CASCADE |
| type | Char choices | request_received, request_accepted, request_rejected, request_cancelled, message_received, session_upcoming, session_rescheduled, session_cancelled, confirmation_recorded, exchange_completed, review_received |
| title | Char | |
| body | Text, blank | |
| target_url | Char | deep link (R4) |
| is_read | bool, default F | |
| read_at | DateTime, null | |

- **Index:** `(recipient, is_read, created_at)`. No GenericForeignKey (R4).

### Review (`reviews`) — N-1 Exchange (PROTECT), reviewer/reviewee FK User (PROTECT)
| Field | Type | Notes |
|---|---|---|
| exchange | FK(Exchange) | PROTECT |
| reviewer | FK(User) | PROTECT |
| reviewee | FK(User) | PROTECT |
| rating | int | validated 1–5 |
| feedback | Text | |

- **Constraint:** `unique(exchange, reviewer)` → one review per participant per exchange.
- Create only when `exchange.status == COMPLETED`; updates `UserProfile.rating_avg/rating_count` transactionally.

### UserBlock (`moderation`) — blocker/blocked FK User (CASCADE)
| Field | Type | Notes |
|---|---|---|
| blocker | FK(User) | CASCADE |
| blocked | FK(User) | CASCADE |
| reason | Char, blank | |

- **Constraint:** `unique(blocker, blocked)`; check `blocker != blocked`.
- **Index:** `(blocker)`, `(blocked)` for match exclusion.

### UserReport (`moderation`) — reporter/reported FK User (PROTECT)
| Field | Type | Notes |
|---|---|---|
| reporter | FK(User) | PROTECT |
| reported | FK(User) | PROTECT |
| reason | Char choices | |
| description | Text | |
| status | Char choices | `OPEN`/`REVIEWING`/`RESOLVED`/`DISMISSED` |
| handled_by | FK(User), null | SET_NULL (staff) |
| handled_at | DateTime, null | |

## Delete-behavior summary
- **CASCADE:** profile, confirmations, messages, sessions, notifications, blocks, Google connection.
- **PROTECT:** skills, requests, exchanges, reviews, reports (preserve history).
- **SET_NULL:** `suggested_by`, `cancelled_by`, `handled_by`, `previous_session`.
- Users are deactivated/suspended, not deleted — PROTECT chains rarely trigger.
