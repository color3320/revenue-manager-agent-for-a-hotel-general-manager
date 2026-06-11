---
name: data-traps-and-definitions
description: Use when interpreting any tool output and you need to avoid misreading counts, dates, revenue fields, or ADR — not to re-learn metric definitions.
---

# Data traps and definitions

## When to use

Load this skill before narrating tool output when you are unsure whether a number is bookings, nights, rows, or revenue — or when the GM question spans multiple date or revenue concepts.

## Tools to call

- `describe_dataset` — as-of date, capacity, lookup codes, window definitions.
- Any metric tool — always read its `filters_and_definitions` and `caveats` before speaking.

Do not restate formulas here; the tool envelope is the definition.

## Comparison baselines

Before quoting a number, check:

- **What is being counted?** Reservations, room nights, stay rows, or revenue — they differ by design.
- **Which window?** OTB (forward stays), STLY (past comparable stays), current (180-day arrival lookback), pace (booking date), or cancellation date.
- **Which revenue?** Total (room + package) vs room-only — match the question.
- **Capacity context:** 98 physical rooms (`describe_dataset` → `room_capacity`) — nights share vs capacity matters for compression.

## Interpretation

**Healthy:** You cite a number and can point to the exact filter in `filters_and_definitions`. Headline matches the tool's `headline` grain.

**Concerning:** You mix metrics without noticing — e.g. "514 reservations on the books" when 514 is room nights and 250 is reservations. A GM acting on the wrong grain makes wrong pricing and staffing calls.

## Heuristics

- If two numbers from the same question differ by ~10–15%, you probably mixed grain — stop and re-read the envelope.
- When the verify page or GM mentions "455" — that is a stale brief figure; trust `describe_dataset` and OTB tools, not memory.
- `total_stay_rows` (549) includes cancelled and past nights; OTB room nights (514) is the forward reserved inventory number.

## Trap

The most common briefing failure is **quoting the right tool with the wrong instinct**: reading 549 stay rows as OTB, or counting rows as bookings, or using booking-date pace as forward inventory. The tool may be correct; the narration swaps concepts.

## Recommendation levers

When you catch a trap in your own reasoning:

1. Re-run the purpose-built tool rather than adjusting mentally.
2. State the assumption explicitly: "This is OTB room nights on stay_date ≥ as-of, cancelled excluded."
3. If the GM's question truly needs a definition the tools do not cover, say so — do not fill the gap with improvised SQL.

## Briefing scaffold

> **Headline:** [One commercial fact, correct grain]
> **Drivers:** [Segment or window from tool filters]
> **Risk:** [What goes wrong if this number is misread]
> **Action:** [Re-query with correct tool/args, or clarify with GM]
