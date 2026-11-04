# Requirements Traceability

Maps every functional module, absolute rule, and cross-cutting requirement to the phase that delivers it and the signal that proves it is done. A requirement is **not** complete because a page renders — it is complete when its acceptance signal (tests + manual verification) passes.

Phases are defined in [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md).

## Functional modules

### M1 — Authentication & Account Management → P2
| Requirement | Acceptance signal |
|---|---|
| Registration | new account created; duplicate email rejected |
| Login / logout | session established / cleared |
| Secure password hashing | PBKDF2 hash stored; plaintext never persisted |
| Forgot/reset password | reset token flow works (console backend if no SMTP) |
| Email verification *(if SMTP approved)* | unverified cannot access gated areas; else deferred (see R7) |
| Custom User, email login, optional username | `USERNAME_FIELD="email"`; username optional |
| Profile create/edit, avatar upload, settings | own profile editable; avatar validated |
| Account deactivation | deactivated user excluded from discovery/login |
| Session management | secure cookies in prod |

### M2 — User Profiles → P2
| Requirement | Acceptance signal |
|---|---|
| Fields: name, avatar, bio, location, experience, offered/wanted skills, member-since, completed count, avg rating, review count | all present on profile |
| No cross-user private edits | editing another user's profile → 403 |
| Auth required to view others | anonymous access to profiles → redirect/403 |

### M3 — Skill Management → P3
| Requirement | Acceptance signal |
|---|---|
| Categories, individual skills, search | catalogue browsable/searchable |
| Offered/wanted lists, remove, proficiency, notes, learning goals | OFFER/WANT CRUD works |
| Prevent duplicate skill records | canonical uniqueness enforced (DB constraint) |
| User-suggested skills → admin approval | suggestion saved `PENDING`; only `APPROVED` appears in catalogue/matching |

### M4 — Discovery & Mutual Matching → P4
| Requirement | Acceptance signal |
|---|---|
| **Strict mutual match (both directions)** | A↔B match only when each offers what the other wants |
| One-way is not a match | one-direction overlap → excluded |
| Search by skill, filter by category/proficiency | filters narrow results |
| Show which skills each can teach the other | bidirectional exchangeable skills displayed |
| Exclude self, blocked, **deactivated**, suspended | none appear in results |
| On-demand ORM calculation | no match store/infrastructure |
| Server re-validation on request create & accept | stale frontend match cannot create/accept |

### M5 — Exchange Requests → P5
| Requirement | Acceptance signal |
|---|---|
| Send w/ intro message; view sent/received | lists correct per user |
| Accept / reject / cancel | receiver accepts/rejects; sender cancels |
| Only valid mutual matches can be requested | invalid match → rejected server-side |
| No duplicate pending per pair | second pending → rejected |
| Blocked pairs cannot request | blocked → rejected both directions |
| Accept creates exchange atomically | request+exchange consistent in one transaction |

### M6 — Exchange Lifecycle → P6
| Requirement | Acceptance signal |
|---|---|
| Exactly two participants; ONGOING/COMPLETED/CANCELLED | states enforced |
| Workspace shows participants, agreed skills, details, progress, chat & session access, confirm, cancel | all present |
| **Dual completion confirmation** | first confirm → still ONGOING; second → COMPLETED |
| Separate confirmation per participant | `ExchangeConfirmation` row per user |
| Transactions + uniqueness prevent dup/races | concurrent double-confirm safe; one row per user |
| Frontend never decides completion | status derived server-side only |
| Terminal states not reopened | COMPLETED/CANCELLED immutable via ordinary requests |

### M7 — Private Messaging → P7
| Requirement | Acceptance signal |
|---|---|
| Send/receive, history, sender+timestamp | thread renders correctly |
| Unread indicators, mark-read | unread count accurate |
| Polling for new messages | `?since=` returns new only |
| Participants-only access | non-participant → 403 on every request |

### M8 — Learning Session Scheduling → P8
| Requirement | Acceptance signal |
|---|---|
| Create session w/ title, desc, start/end | session persisted |
| Upcoming/past views; reschedule; cancel | lists + transitions correct |
| Statuses SCHEDULED/COMPLETED/CANCELLED/RESCHEDULED | enforced |
| Participants-only management | non-participant → 403 |
| Timezone-aware datetimes | `USE_TZ=True`; stored UTC, rendered local |

### M9 — Google Calendar & Meet → P9
| Requirement | Acceptance signal |
|---|---|
| OAuth 2.0 connect, min scopes | consent stores tokens (encrypted) |
| Create event + Meet on schedule; store event id + Meet URL | link shown to participants only |
| Update on reschedule; delete on cancel | event synced |
| Refresh expired tokens; handle revoke/reconnect | mocked refresh/revoke tests pass |
| Prevent duplicate events; handle pending Meet | idempotent; `PENDING→SYNCED/FAILED` |
| App works when Google unavailable | integration disabled → sessions still usable |
| Tokens never exposed (API/template/log/git) | serializers/log scrubbed |

### M10 — Notifications → P10
| Requirement | Acceptance signal |
|---|---|
| DB-backed in-app for all listed triggers | each event creates a notification |
| List, read/unread, mark one, mark all, history | state correct |
| Links to relevant page | `target_url` resolves |
| Email *(if SMTP approved)* | optional; deferred otherwise |

### M11 — Reviews & Feedback → P11
| Requirement | Acceptance signal |
|---|---|
| Rating 1–5 + written feedback | persisted |
| Only after COMPLETED | pre-completion review → rejected |
| Participants only; one per participant per exchange | duplicate → rejected |
| Profile aggregate (avg + count) | updates transactionally |

### M12 — Blocking, Reporting & Moderation → P12
| Requirement | Acceptance signal |
|---|---|
| Block/unblock | block persisted/removed |
| Blocked excluded from discovery/match; cannot request either way | verified exclusion |
| Existing exchanges remain intact on block | exchange/chat/sessions continue (R5/R17) |
| Report w/ reason + description | report persisted |
| Admin report mgmt, suspend, deactivate | staff-only actions |
| Manage categories; approve suggested skills | catalogue curated |
| No private-data exposure to unauthorized | authorization enforced |

## Absolute rules (all phases)
| Rule | Enforcement |
|---|---|
| Non-monetary / no credits | no payment/credit models or endpoints exist |
| No AI features/branding | no AI deps; no AI copy (see UI_DESIGN_SYSTEM) |
| No public feed | no feed endpoints/pages |
| Meet via Calendar only | only `integrations` app touches Google |
| Stack locked | no forbidden deps in `requirements.txt` |
| No fake data | seed data clearly labeled; no fabricated stats/reviews |

## Cross-cutting
| Requirement | Phase |
|---|---|
| Security baseline (CSRF, object perms, hashing, upload validation, throttling, secrets, audit) | all; hardened P14 |
| Per-module tests | each phase; full sweep P14 |
| `/api/v1/` DRF conventions | P5 onward; documented P13 |
| Sky-Blue design system | P1 tokens; applied each UI phase |
| Documentation in `docs/` | P0 (this set); updated per phase |
