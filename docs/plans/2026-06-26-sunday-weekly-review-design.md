# Sunday Weekly-Review Mode — Design

**Date:** 2026-06-26
**Status:** Design approved (rev 2, post adversarial review) — not yet built
**Author:** Anand (with Claude)
**Review:** `2026-06-26-sunday-weekly-review-design-review-1.md` (verdict NEEDS_REVISION;
all critical issues addressed below)

## Goal

On Sundays, swap the dashboard's bottom-left zone to a **weekly-review** view:
auto-derived **wins / misses this week** plus **next week's focus** (top goals).
A time-aware layout change — the zone reverts to the normally-configured widget
Mon–Sat. Glanceable, no-interaction, pure-compute from data we already have.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Scope | Swap only the bottom-left (`week`) zone | Already the configurable slot; keeps today/habits/goals visible to review against. |
| Wins / misses | Auto-derived from data | Habits (done vs target), tasks done this week. No new capture pipeline; always accurate. |
| Next-week "3 big rocks" | Derived from goals | Reuses goal data; real on-screen content; no new storage. (Hand-set rocks via capture pipeline — deferred.) |
| Activation | `SUNDAY_REVIEW` toggle (default on) | Auto-overrides bottom-left on Sundays only; reverts Mon–Sat. |
| Reliable rollover | **Core daily-tick daemon** | The only always-on re-render path; works with all features off; also fixes the pre-existing stale-header-date bug. |

The review content is **pure-compute from the existing store** — no new table, no new
data source, no glasses involvement. The only infra addition is the tick daemon.

## Changes from rev 1 (per review)

1. **Day-rollover gap (critical).** Added a core daily-tick daemon — see *Re-render &
   activation*. Rev 1 hand-waved this as "picked up by the poller"; the reviewer
   confirmed no always-on tick exists when calendar+weather are both off.
2. **`due` formatting** for None / past / today / unparseable now specified.
3. **Goal ranking** interleaving + stable tie-breaks now defined; `get_goals()` to
   expose `id` for a deterministic final sort key (avoids spurious e-ink refreshes).
4. **Task week boundary** pinned to the *same* naive-local Monday `get_habits()` uses;
   Monday computed once in the renderer and passed down.
5. **Mockup ↔ rules** reconciled: wins and misses are each **one compact line**
   (up to 3 items inline), not 3 lines each.
6. **`_truncate`** moved to a shared location to avoid a widget→renderer import cycle.

## Architecture

```
if config.sunday_review and today.weekday() == 6:   # Sunday (Mon=0..Sun=6)
    review.render(draw, box, {"review": build_review(...)})
else:
    <existing week / life / weekofyear / yearprogress dispatch>
```

Mon–Sat are unchanged. The override touches only the bottom-left zone. `today` is the
single `dt.date.today()` the renderer already computes (renderer.py:237) — not recomputed.

New files, mirroring existing patterns:

- **`app/review.py`** — *pure core* (sibling to `agenda.py` / `weatherview.py`).
  `build_review(habits, tasks_done_count, goals, today) -> {"wins", "misses", "rocks"}`.
  No I/O, no store import → fully unit-testable (template: `tests/test_agenda.py`).
- **`app/widgets/review.py`** — `render(draw, box, ctx)` (sibling to `today.py` etc.).
- **`app/daily_tick.py`** — small always-on daemon (mirrors `weather/sync.py`'s
  `start_background()` thread shape) that calls `renderer.render_if_changed()` on a
  cadence. Started unconditionally from `api.py` startup.

Shared helper move:

- **`_truncate`** relocated from `renderer.py` to **`theme.py`** (which already holds
  fonts); `renderer.py` and `widgets/review.py` both import it. Avoids the
  widget→renderer back-import cycle (renderer imports widgets).

Data, all from the existing store:

- `habits` — `store.get_habits()` (keys `name, week, done, target, streak`; `target`
  is nullable).
- **New store helper** — `store.get_tasks_done_this_week(monday)`: `COUNT(*)` of `task`
  rows with `status='done'` and `date(done_at) >= :monday`. `monday` is passed in
  (computed once by the renderer) so the task window matches the habit week exactly.
- `goals` — `store.get_goals()` extended to also select **`id`** (stable sort key).

## Re-render & activation (daily-tick daemon)

**Problem (verified):** the only re-render paths are the calendar poller, the weather
poller, and glasses photo/bot events — all opt-in/event-driven. With calendar and
weather both off, nothing re-renders on time, so the screen can sit on Saturday's image
through Sunday (and the header date never advances).

**Fix:** `app/daily_tick.py` runs a daemon thread that calls
`renderer.render_if_changed()` on a fixed cadence (default **every 60 min**, env
`DAILY_TICK_MINUTES`). `render_if_changed()` already hashes the PNG and only bumps the
version on a real pixel change, so hourly ticks are cheap and cause **zero** extra
e-ink refreshes on days where nothing changes. Activation latency into Sunday is ≤ the
tick interval. Started from `api.py` startup, unconditionally (independent of any
feature flag). Side benefit: the header date now advances on its own.

## Compute rules

**Wins / misses (habits + tasks):**

- Each habit with a non-null `target_per_week`: `done >= target` → **win**
  (`"Gym 5/5"`); `done < target` → **miss** (`"Read 2/5"`). Habits with `target is
  None` are skipped (no pass/fail signal). Guard against `target == 0` (skip; no
  division).
- Tasks: append the string `"N tasks done"` to wins when `N > 0`.
- Goal-progress deltas are **out of scope** — no historical snapshots exist (YAGNI).
- **Each of wins and misses is rendered as one compact line with up to 3 items**
  inline (e.g. `Wins: Gym 5/5 · Water 7/7 · 8 tasks done`). Order misses by largest
  shortfall (`target - done`, then `id`); order wins by highest ratio `done/target`
  (then `id`). Items beyond 3 are dropped (line stays single).

**Next-week focus (goals):** two groups, concatenated:
1. Goals **with** a `due` date, ascending `due` (then ascending `id`).
2. Goals **without** a `due` date, ascending `progress` (then ascending `id`).
Take the **top 3**. The trailing `id` key makes the cut deterministic across renders.

Per-goal suffix:
- valid `due` in the future → `"(due Nd)"` where `N = (due - today).days`.
- `due == today` → `"(due today)"`.
- `due` in the past → `"(overdue)"`.
- `due is None` or unparseable (parse defensively, mirroring `renderer._parse_date`
  which returns `None`) → `"(P%)"` using `progress` (e.g. `"(60%)"`).

## Layout

Bottom-left zone is **1280 × 605 px** (measured: `_zones()` → header 144, footer 86,
body 1210, row 605, col 1280; usable text width ≈ 1224 px). At font 32 the longest
real lines measure ~555–566 px — **comfortably within budget**; `_truncate` only
engages on pathologically long goal/habit text. Height budget ≈ 9 lines; the layout
uses 8:

```
★ THIS WEEK
  Wins: Gym 5/5 · Water 7/7 · 8 tasks done
  Misses: Read 2/5 · Meditate 1/4
  ──────────────────────────────
  NEXT WEEK — focus
  1. Ship side project (60%)
  2. Trip planning (due 18d)
  3. Learn piano (overdue)
```

- The star is a **drawn INK primitive** (font-safe, like the weather glyphs and the
  Now/Next dot) — no emoji on e-ink.
- The `·` separator is DejaVu-safe (already used by the Now/Next banner and footer).
- Long lines truncated with the shared `_truncate` helper.

## Edge cases

- **0 goals** → focus shows a calm prompt (`"Set goals to see focus"`).
- **<3 goals** → show what exists.
- **No targeted habits / no wins / no misses** → show `"—"` rather than an empty block.
- **`target == 0` or `None`** → habit skipped (no division, no false miss).
- **`due` past / today / None / unparseable** → handled per the suffix rules above.
- **Overflow** → truncate + the 3-item / 3-goal caps.
- **Rollover** → handled by the daily-tick daemon (≤ tick interval latency).

## Testing

`tests/test_review.py` (pure, no rendering; frozen `today`):

- Wins/misses correctness (done vs target; `target=None`/`0` skipped; tasks-done line).
- 3-item cap and ordering (shortfall for misses, ratio for wins, `id` tie-break).
- Goal ranking: dated-before-undated interleaving; due-ascending then progress;
  `id` tie-break determinism.
- `due` suffix: future (`Nd`), today, past (`overdue`), None/unparseable (`P%`).
- Empty-data fallbacks: no goals (prompt), no targeted habits, no tasks done, <3 goals.

`store` test: `get_tasks_done_this_week(monday)` counts only `status='done'` rows on/after
the given Monday (boundary: a task done exactly at Monday 00:00 counts; Sunday-prior
does not).

## Out of scope

- Hand-set "big rocks" via the notebook/glasses capture pipeline (would reuse the
  `add_to_review()` TODO in `store.py`) — deferred.
- Goal-progress-delta wins (needs progress history snapshots).
- Configurable review day / full-body Sunday layout — deferred.
- A precise midnight-aligned tick (hourly cadence is sufficient and simpler).
