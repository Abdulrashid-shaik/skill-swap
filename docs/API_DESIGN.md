# API Design

JSON API under `/api/v1/`, built with Django REST Framework. Template pages render HTML; these endpoints back the dynamic (`fetch`) interactions and all business state transitions. This inventory is filled in and documented per phase; endpoints are representative, not final.

## Conventions

- **Auth:** DRF `SessionAuthentication` (shares the Django login session). No JWT unless approved.
- **CSRF:** required on all state-changing requests; JS sends `X-CSRFToken` from the cookie.
- **Permissions:** `IsAuthenticated` by default + **object-level** checks (e.g. exchange participants only). Staff-only for moderation.
- **Validation:** all business rules enforced in serializers/views, never assumed from the client.
- **Pagination:** `PageNumberPagination` on list endpoints.
- **Filtering:** DRF/ORM query params (no `django-filter` unless approved — R10).
- **Errors:** consistent envelope from `common`, e.g. `{"detail": "...", "code": "...", "fields": {...}}`.
- **Throttling:** `UserRateThrottle` / `ScopedRateThrottle` on auth, request-create, messaging, reports.
- **Never exposed:** passwords, OAuth tokens, internal moderation notes, other users' private data.

## Endpoint inventory

| Domain | Method + path | Purpose | Phase |
|---|---|---|---|
| Auth | `POST /auth/register/` | create account | P2 |
| | `POST /auth/login/` · `POST /auth/logout/` | session in/out | P2 |
| | `POST /auth/password/reset/` · `POST /auth/password/reset/confirm/` | reset flow | P2 |
| | `POST /auth/verify-email/` | email verify *(if SMTP)* | P2 |
| Profile | `GET/PATCH /profiles/me/` | own profile | P2 |
| | `GET /profiles/{id}/` | public profile (auth only) | P2 |
| | `POST /profiles/me/avatar/` | avatar upload | P2 |
| | `POST /accounts/deactivate/` | deactivate account | P2 |
| Skills | `GET /skills/` · `GET /skills/categories/` | catalogue (APPROVED) | P3 |
| | `GET/POST/DELETE /my-skills/` · `PATCH /my-skills/{id}/` | OFFER/WANT management | P3 |
| | `POST /skills/suggest/` | suggest new skill (→ PENDING) | P3 |
| Discovery | `GET /discovery/matches/` | mutual matches | P4 |
| | `GET /discovery/search/?skill=&category=&proficiency=` | filtered discovery | P4 |
| Requests | `GET/POST /requests/` · `GET /requests/sent/` · `GET /requests/received/` | list/create | P5 |
| | `POST /requests/{id}/accept/` · `/reject/` · `/cancel/` | transitions | P5 |
| Exchanges | `GET /exchanges/` · `GET /exchanges/{id}/` | list/detail | P6 |
| | `POST /exchanges/{id}/confirm/` | **dual-confirm** | P6 |
| | `POST /exchanges/{id}/cancel/` | cancel | P6 |
| Messaging | `GET /exchanges/{id}/messages/?since=` | poll messages | P7 |
| | `POST /exchanges/{id}/messages/` | send | P7 |
| | `POST /messages/{id}/read/` | mark read | P7 |
| Scheduling | `GET/POST /exchanges/{id}/sessions/` | list/create | P8 |
| | `PATCH /sessions/{id}/` · `POST /sessions/{id}/reschedule/` · `/cancel/` | manage | P8 |
| Google | `GET /integrations/google/connect/` · `GET /integrations/google/callback/` · `POST /integrations/google/disconnect/` | OAuth dance | P9 |
| Notifications | `GET /notifications/` | list | P10 |
| | `POST /notifications/{id}/read/` · `POST /notifications/read-all/` | mark read | P10 |
| Reviews | `GET /exchanges/{id}/reviews/` · `POST /exchanges/{id}/reviews/` | view/create | P11 |
| Moderation | `POST /moderation/block/` · `POST /moderation/unblock/` | block/unblock | P12 |
| | `POST /moderation/report/` | report user | P12 |
| | staff: reports queue, suspend, approve-skill, category mgmt | moderation | P12 |

## Implementation notes

- Prefer `ModelViewSet` + `DefaultRouter` where CRUD fits; use `@action` for state transitions (accept, confirm, reschedule, read).
- Business-transition endpoints return the updated resource plus any derived state (e.g. confirm returns exchange status so the UI reflects server truth).
- Full request/response schemas are documented as each phase lands; consolidated in P13.
