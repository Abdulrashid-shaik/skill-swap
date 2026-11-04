# Development Roadmap

One module at a time. A phase is complete only when its acceptance criteria pass (automated tests **and** manual verification) — never because a page renders. Each phase follows the professional workflow in [`../CLAUDE.md`](../CLAUDE.md): explain → requirements → dependencies → DB changes → endpoints → UI → security/edge cases → acceptance criteria → implement in small steps → tests → run tests → manual verify → review → docs → summary → commit.

## Dependency map

```
common ──► (everything)
accounts ──► skills ──► discovery ──► exchanges ──► {messaging, scheduling, reviews}
                                          │                         │
                                          └──► notifications ◄───────┘  (hooks into events)
scheduling ──► integrations (Google)   [externally gated]
moderation ──► {accounts, skills, discovery, exchanges}
```

Critical path: `common → accounts → skills → discovery → exchanges(requests → lifecycle)`. `notifications` and `moderation` cross-cut. `integrations` is the only externally-blocked node.

## Phases

| Phase | Scope | Acceptance criteria |
|---|---|---|
| **P0** Architecture & docs | this documentation set | all requirements represented; approved |
| **P1** Foundation | venv, Django 5.2 + DRF install *(approval)*, `config/` settings split, SQLite+WAL, `common` base model, base template + **Sky-Blue tokens**, `.env.example`, `.gitignore` | project boots; smoke test green; design tokens load |
| **P2** Auth & profiles | custom `User` (email login), `UserProfile`, register/login/logout, password reset, avatar *(Pillow approval)*, deactivation, suspension fields | tests: register/login/logout/reset/deactivate pass; **cross-user edit denied**; User migrated once |
| **P3** Skills | `SkillCategory`, `Skill` (+approval workflow), `UserSkill`, catalogue, OFFER/WANT, suggest→approve | canonical uniqueness enforced; PENDING hidden; APPROVED visible |
| **P4** Discovery & matching | matching service, discovery/search, filters | **both-direction match** passes; **one-way/self/blocked/deactivated/suspended excluded** |
| **P5** Exchange requests | `ExchangeRequest`, send/accept/reject/cancel | no dup pending; blocked blocked; accept re-validates + atomic exchange create |
| **P6** Exchange lifecycle | `Exchange`, `ExchangeConfirmation`, workspace, cancel | **first confirm ≠ complete; second → COMPLETED; concurrent double-confirm safe**; terminal immutable |
| **P7** Messaging | `Message`, polling, unread/read | participant-only 403 tests; `?since=` returns new only |
| **P8** Scheduling | `ExchangeSession`, tz-aware, reschedule/cancel | ownership checks; tz-aware storage; reschedule chain |
| **P9** Google Cal/Meet | `integrations` app, OAuth, event+Meet, refresh/revoke | mocked refresh/revoke/failure pass; **app runs with integration disabled**; tokens never exposed |
| **P10** Notifications | `Notification`, triggers, read/mark-all | each event creates correct notification; `target_url` resolves |
| **P11** Reviews | `Review`, post-completion, aggregate | pre-completion rejected; one per participant; aggregate updates |
| **P12** Moderation | `UserBlock`, `UserReport`, admin suspend/approve | block hides+forbids, exchange intact; report created; staff-only |
| **P13** API completion & docs | finalize `/api/v1/`, error envelope, full endpoint docs | every endpoint documented; consistent errors |
| **P14** Testing, security, optimization | security review, throttling, coverage, SQLite concurrency | review passes; concurrency tests green |
| **P15** Deployment & final docs | prod settings, deployment doc, final documentation | prod config verified; docs complete |

## Per-phase gate

Do not advance until the current phase's acceptance criteria pass. At each phase end: summarize changed files + test results and recommend a Git commit message. Scope changes require approval before implementation.

## External gates

- **P2/P10 email:** needs company SMTP (else deferred; dev console backend) — R7.
- **P2 avatars:** Pillow install approval — R14.
- **P9 Google:** OAuth credentials + company approval + token-encryption library approval — R6/R8.
- **Timed reminders (P10):** OS cron permission — R11.

See [DECISIONS.md](DECISIONS.md) for the full decision log.
