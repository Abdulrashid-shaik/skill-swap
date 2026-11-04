# SkillSwap — Project Brief

> Condensed, authoritative summary. For detail, follow the linked documents — this file does not duplicate them.

## Vision

SkillSwap is a peer-to-peer skill exchange platform. Members list skills they can **teach** and skills they want to **learn**, discover **mutually compatible** partners, request an exchange, communicate privately, schedule learning sessions (optionally via Google Meet), confirm completion, and review each other. Knowledge is exchanged directly, without money.

**Canonical example:** User A teaches Python, wants UI/UX. User B teaches UI/UX, wants Python. Each offers what the other wants → a valid mutual match.

## The 10 Absolute Rules (never violate)

1. Completely non-monetary platform.
2. No payments, wallets, credits, points, tokens, subscriptions, or paid mentoring.
3. No AI-powered features or AI branding.
4. Never market or describe the product as AI-powered.
5. No public social-media feed.
6. No custom video-conferencing system.
7. Google Meet only through Google Calendar.
8. No unnecessary technologies or infrastructure.
9. No fake statistics, fake activity, or fabricated reviews.
10. Never implement features that contradict requirements without asking first.

## Locked Technology Stack

- **Backend:** Python 3.12+, Django 5.2 LTS (env-compat), Django REST Framework, Django ORM.
- **Frontend:** HTML5, CSS3, Django Templates, vanilla JavaScript, Fetch API.
- **Database:** SQLite **only**. No Postgres/MySQL/Mongo, no external DB hosting.
- **Auth:** Django session auth + DRF `SessionAuthentication`, CSRF on writes. No JWT unless approved.
- **Forbidden:** React, Angular, Vue, Next.js, Node.js/npm builds, Redis, Celery, mandatory WebSockets, microservices, unnecessary external dependencies.
- **Chat:** JavaScript polling against Django APIs (no Redis/WebSockets).

New dependencies require an explanation and explicit approval before install.

## Document Map

| Document | Purpose |
|---|---|
| [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) | Every requirement → phase → acceptance signal |
| [ARCHITECTURE.md](ARCHITECTURE.md) | App structure, config, request flow |
| [DATABASE_ERD.md](DATABASE_ERD.md) | Entities, fields, constraints, delete behavior |
| [BUSINESS_RULES.md](BUSINESS_RULES.md) | Matching, state machines, dual-confirmation |
| [API_DESIGN.md](API_DESIGN.md) | `/api/v1/` inventory and conventions |
| [UI_DESIGN_SYSTEM.md](UI_DESIGN_SYSTEM.md) | Sky-Blue design system, pages, voice |
| [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) | Phases P0–P15 + acceptance criteria |
| [DECISIONS.md](DECISIONS.md) | Architecture Decision Records + R1–R17 |

Root [`CLAUDE.md`](../CLAUDE.md) tells future sessions how to use these documents.
