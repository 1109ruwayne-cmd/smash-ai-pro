# Smash AI Pro — workspace

Created 17 November 2026. Everything here is downstream of one decision: **Smash AI Pro is the product; the rest are sub-agents, namespaces, or models.**

---

## What's in this workspace

| File | What it is | Status |
|---|---|---|
| `smash-ai-pro-multiplatform.md` | Decision memo: is one multiplatform app possible, and what blocks it | done |
| `smash-ai-pro-subagent-registry.md` | How the portfolio maps onto agents / tools / models | done |
| `RUNNING.md` | **How to run the app** — the build, and its security posture | live |
| `smash/` | Working core: gate, audit chain, orchestrator, HTTP server, UI | 1,448 lines |
| `registry/tool_contract.py` | Namespace + allowlist contract (RUW-21) | 233 lines |
| `SECURITY.md` | **Security posture** — proven controls, known gaps, hard limits | 162 tests |
| `tests/` | 140 tests across eight suites | **all green** |

**Run it:**

```bash
export SMASH_GATE_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
export SMASH_SESSION_SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
python3 -m smash.auth add you --role admin   # per-operator, not a shared password
python3 -m smash.server --port 8000      # open http://localhost:8000
python3 -m pytest tests/ -q              # 69 passed
```

Recorded outside this workspace:
- **Notion** — *Smash AI Pro — Decision Record (2026-11-17)*
- **Linear** — project *Smash AI Pro — Unified Product* with RUW-21 → RUW-24

---

## The decision, compressed

**Keep** Smash AI Pro as the only product name.

**Absorb** what only makes sense inside orchestration: Creative Studio, Training Studio, Research, Engineering.

**Federate** what has its own customers and its own store listing: Aegis → `security.*`, Purify → `content.*`, Lead Rescue → `automation.*`. They keep their front doors and become sub-agents behind the gate.

**Don't merge** SA Registration Hub — a statutory compliance surface sharing an operator identity with a dev platform only widens the POPIA exposure.

**Models are a separate registry.** Aegis is not a model; it's a persona plus gated tools. Your own fine-tuned GGUFs join the gateway registry after RUW-17.

---

## Why the contract came first

Your least-privilege guarantee rests on one assertion: *every plan step's agent may use its tool.* Folding five products into one fabric is exactly what breaks it — and if it breaks, the approval gate protects nothing, because everything is reachable from one persona.

So `registry/tool_contract.py` enforces three invariants at registration time:

- **I1** ids are `module.verb`, unique, and the module is a *declared namespace* — two products cannot both register `scan`
- **I2** every tool declares a danger level; there is no default, because a default of "harmless" is a silent privilege grant
- **I3** grants are explicit, per-agent, immutable, and contain no wildcards

### The thing that makes it trustworthy

The suite was proven by breaking it, not by watching it pass:

```
add "analysis" to automation.send   → 3 tests fail, including
                                      test_analysis_cannot_reach_send
two products register security.scan → REFUSED: duplicate tool id
grant "*" or "automation.*"         → REFUSED: wildcard not permitted
```

`test_l3_grant_map_is_exact` enumerates every L3 tool and its exact holders. Adding an agent to an L3 allowlist without a deliberate test edit fails the build — so privilege can only widen when someone is looking at it.

### One design call worth knowing about

Purify owns `content.*` but is *wielded by* the automation division. Rather than invent a sixth division, the contract separates:

```python
DIVISIONS           = {engineering, research, data, security, automation}
PRODUCT_NAMESPACES  = {content}
NAMESPACES          = DIVISIONS | PRODUCT_NAMESPACES
```

The org chart stays five divisions; the fabric stays honest about who owns which tools. A namespace must be declared before it can register anything — an undeclared one is either a typo or an undesigned product, and both should fail loudly.

---

## Order of operations

| # | Do this | Issue | Why now |
|---|---|---|---|
| 1 | Land the registry contract | **RUW-21** | Precondition for everything else |
| 2 | Freeze bundle ID + package name, rebrand four surfaces | **RUW-22** | Effectively permanent once submitted |
| 3 | Get the URL up (`docker compose`, RUW-19 item 1) | RUW-19 | Same unlock for stores, privacy policy, HN |
| 4 | Confirm Play account type; start closed test if personal | **RUW-24** | 14 days of calendar you cannot compress |
| 5 | Moderation: filter, report, block | RUW-24 | Apple 4.7.1 — retrofit costs a review cycle |
| 6 | Federate the three products | **RUW-23** | Blocked by 1 |
| 7 | Own models in the gateway | RUW-17 | Last, and smallest |

Steps 1, 2 and 4 are today's work. Step 4 is the only one where delay is unrecoverable.

---

## Deliberately not built here

- **The federated adapter** (RUW-23). It depends on whether your orchestrator has an MCP client — if not, authenticated HTTP adapters do the same job with less novelty. Verify before building; I didn't want to hand you a shape that assumes an answer.
- **Anything touching the gate itself.** RUW-15 already scopes signed single-use approvals, and the contract is designed to sit *under* it, not beside it.
- **SA Registration Hub integration.** Out of scope by decision, not by omission.

## Caveats

- Adopt-and-verify: `registry/tool_contract.py` is a reference, not a patch against your real `tools/registry.py`. The three invariants are the point; the class layout can bend to your existing code.
- Your existing 8 agents need grants written for them — the default registry here demonstrates the shape, it is not your production allowlist.
- I inferred the Aegis / Purify / Lead Rescue tool surfaces from their names and launch packs; I did not read their source. Confirm each tool's real danger level before granting anything L2, and be conservative about L3.
