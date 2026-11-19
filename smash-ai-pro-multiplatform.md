# Smash AI Pro — combining the AI apps into one multiplatform product

**Date:** 17 November 2026
**Status:** Decision memo — technical answer is yes; the blockers are not technical
**Sources:** Notion *OMNITECH AI — Architecture & Implementation Plan*, *GORO AI — Product Hunt Launch Kit*, Linear team RUW, Apple App Review Guidelines 4.2 / 4.7, Google Play closed-testing policy

---

## The answer in one line

Yes, it's possible — and you're closer than you think, because your architecture already decided this for you. But **don't combine them into one app icon.** Make Smash AI Pro one branded product with capability modules inside it, running one shared backend behind three thin shells.

---

## Why "yes" is mostly already true

Your own notes say this, not me:

- **"The UI is already a single HTML file with no build step, so it embeds directly in a webview — no rewrite needed for the desktop shell."** (RUW-18)
- **5.7k lines, 54 passing tests, 20 tools, 8 agents, 37 API routes** on one API (Architecture §1, now ~104 tests per RUW-20)
- **Model layer is provider-agnostic** — a deterministic local engine with zero keys, one key away from live
- **RUW-18 already scopes exactly this**: Tauri desktop + Expo mobile over one REST API, shared design tokens, one-gesture mobile approval, push notification when a run parks at the gate

So the multiplatform question is not an architecture question. It's a *packaging and distribution* question. Nothing in the codebase fights you.

---

## The trap: five apps in a trench coat

The instinct is to merge GORO, OMNITECH, Smash AI and whatever comes next into one binary. Resist the naming sprawl, not the technical merge.

| Wrong shape | Right shape |
|---|---|
| Five product names, five store listings, five icons | One name: **Smash AI Pro** |
| Divisions as separate apps | Divisions as **modules** inside one app |
| Separate codebases glued together | One repo, one API, three shells |
| Different approval logic per surface | Identical gate semantics everywhere |

**Decide the name now, permanently.** Your Notion has three live names for overlapping things: GORO AI, OMNITECH AI, Smash AI Pro. Your Drive has launch videos branded "smash-ai-pro" and "smash". Bundle ID and package name are effectively forever — an App Store name change costs a review cycle, and a bundle ID change means a new listing with zero history. Pick one, and let the others become module names or get retired.

Your differentiator is stated on the GORO launch kit and it is genuinely good: **"an AI agent platform that can prove what it did."** Because approvals are hash-chained, signed, single-use and audited, the approval gate is the one feature no competitor copies by adding a chat box. Five icons dilute that. One app with a moat sharpens it.

---

## The real blockers (none of them are engineering)

These are already in your own Linear board. A store submission makes every one of them mandatory, so the multiplatform plan and the launch plan are the *same* plan.

### 1. There is no public URL — still blocker #1 (RUW-19)
Every store submission requires a **privacy policy URL, a support URL and a marketing URL**. Apple checks that they resolve. So "fix the URL" isn't a launch prerequisite that competes with the app store — it's the same single unlock for both. `$5 VM + docker compose up` already works per RUW-19.

### 2. PAIA s.51 registration is a hard stop for a SA launch (RUW-20)
Your own audit calls this "the concrete blocker for a SA launch." A file in a repo satisfies nothing — the manual must be lodged with the Information Regulator. Both Apple and Google require you to declare data handling, and a SA consumer app with no registered Information Officer and no cross-border transfer basis (POPIA s.72 / GDPR Ch. V) for briefs sent to a model provider is exposed. **Do this before you submit, not after.**

### 3. Apple Guideline 4.2 — the wrapper rejection
The reported rejection sentence is *"provides a limited user experience as it is not sufficiently different from a mobile browsing experience."* A webview around your command centre fails this.

**You have an unusually clean way to pass it.** Your gate is intrinsically device-shaped:
- Push notification the moment a run parks (RUW-18 acceptance: within 5 s)
- Biometric / passkey approval — approval *should* require the human's face or fingerprint
- Offline approval queue that flushes when the run resumes
- Lock-screen action to deny a parked run

That is two to four genuinely native features tied to a device, and it's the core product rather than a bolt-on. Most wrapper apps have to invent this. You don't.

### 4. Apple Guideline 4.7 — chatbots have their own clause
Anything that can generate user-visible content sits under 4.7 in parallel with 4.2. Section 4.7.1 requires **content filtering, a way to report output, a way to block, and timely responses to concerns** — and your age rating must reflect how often sensitive content can appear. Agent output counts. Budget a real moderation and reporting surface, and don't retrofit it after a rejection.

Note also: 4.7 is the guideline that *permits* HTML5/JS mini apps inside a host app, WebKit/JavaScriptCore only, no native API access — and Apple opened a **Mini Apps Partner Program in November 2025 with halved commissions**. If "my AI apps combined" means hosting modular mini-apps inside a shell, that's the sanctioned route. If it means one integrated product, ignore it and build native.

### 5. Google Play — the 12-tester clock, if your account is personal
A personal developer account created after 13 Nov 2023 cannot reach production until **12 testers stay opted in to a closed test for 14 consecutive days**, and Google then reviews whether those testers actually *engaged*. Internal testing doesn't count. Organization accounts are exempt.

Consequence: **this clock is free but not skippable.** If you're on a personal account, get a closed test live with 15–20 people as early as there's anything installable, and let it run while you fix the rest. Starting it late is the single most expensive sequencing mistake available to you.

### 6. The hidden fork: hosted vs local-first
Your architecture is local-engine-first with zero keys, which is a strength and a fork at the same time. One shared API serving many mobile users means multi-tenancy, per-operator isolation, and someone else's GPU bill. One app that is local by default means each device owns its own store and sync becomes your problem.

Given RUW-20's `operators` table with cascading deletes and pseudonymous audit actors, you already have the tenancy primitives. **Pick hosted multi-tenant as the store product**, and keep the zero-key local engine as the demo/CI path — which is not a compromise, it's the thing that lets a reviewer run your app without you paying for their tokens.

---

## Recommended shape

```
                Smash AI Pro  (one brand, one listing per platform)
        ┌──────────────┬──────────────────┬──────────────────┐
        │  Web         │  Tauri desktop   │  Expo mobile     │
        │  (today)     │  (thin webview)  │  (thin client)   │
        └──────┬───────┴────────┬─────────┴────────┬─────────┘
               └────────────────┼──────────────────┘
                        one REST API — 37 routes
               ┌────────────────┴──────────────────┐
     orchestrator · 20 tools · 8 agents · audit fabric
               ┌────────────────┴──────────────────┐
        gate (signed, single-use) · lessons · provider layer
```

Three non-negotiables across all three shells:
1. **Gate semantics are byte-identical.** Signed, single-use, args-hash bound, replay → 409 (RUW-15). If mobile approval is a softer path, the moat is gone.
2. **Every surface writes the same audit event.** One `appendAudit` shape, no surface-only events.
3. **Mock mode ships in the store build**, so review and CI never need a provider key.

---

## Sequencing

| # | Step | Blocked by | Reuse |
|---|---|---|---|
| 1 | Pick the name. Freeze bundle ID + package name | — | Do it today |
| 2 | Public URL via docker compose (RUW-19 #1) | — | Unlocks stores + channels + privacy URL |
| 3 | Land signed single-use approvals (RUW-15) | — | Prerequisite for mobile approval |
| 4 | PAIA registration + Information Officer + cross-border basis (RUW-20) | Legal practitioner | Store privacy declarations |
| 5 | Moderation: filter, report, block (4.7.1) | — | Needed for both stores |
| 6 | Tauri desktop over existing webview | URL | RUW-18, no rewrite |
| 7 | Expo mobile: overview, runs, one-gesture approve, push | #3 | RUW-18 |
| 8 | Start Play closed test with 15–20 testers | #7 | 14-day clock runs free |
| 9 | Submit to App Store with the gate as the native feature | #2 #4 #5 #7 | — |

Steps 1–5 are worth doing whether or not you ever ship a store app. Step 8 costs nothing but calendar time, and it's invisible until it's urgent.

---

## What I'd tell you to do first

**Pick the name and get the URL up.** Both are unresolved in your own docs, both are cheap, and every other path — stores, Show HN, PAIA, privacy policy — is downstream of them. The multiplatform app is not what's stopping Smash AI Pro. The two-week-old blockers in RUW-19 and RUW-20 are.

The engineering plan to combine them already exists as RUW-18. You don't need a new architecture. You need a URL, a name, and a legal registration.

---

## Caveats on this memo

- Store guidelines change; verify 4.2/4.7 and the Play tester policy against the live pages before you submit.
- I read your Notion architecture note as of 11 Nov and RUW-20 as of 16 Nov. If auth/Postgres landed between them, some status lines above may lag — RUW-20's references to `operators`, HMAC sessions and migrations suggest auth is in, which would remove one precondition I'd otherwise have raised.
- The Play 12-tester rule applies only to *personal* accounts created after 13 Nov 2023. Check which type yours is before planning around it.
