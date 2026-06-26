# Sunday Weekly-Review Mode — Design

**Date:** 2026-06-26
**Status:** Design approved — not yet built
**Author:** Anand (with Claude)

## Goal

On Sundays, swap the dashboard's bottom-left zone to a **weekly-review** view:
auto-derived **wins / misses this week** plus **next week's focus** (top goals).
A time-aware layout change — the zone reverts to the normally-configured widget
Mon–Sat. Glanceable, no-interaction, pure-compute from data we already have.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Scope | Swap only the bottom-left (`week`) zone | Already the configurable slot; keeps today/habits/goals visible to review against. Full-body takeover would hide the very habits+goals you're reviewing. |
| Wins / misses | Auto-derived from data | Habits (done vs target), tasks done this week. No new capture pipeline; always accurate. |
| Next-week "3 big rocks" | Derived from goals | Reuses goal data; real on-screen content all week; no new storage. (True hand-set "rocks" would need a capture pipeline — deferred.) |
| Activation | `SUNDAY_REVIEW` toggle (default on) | Auto-overrides bottom-left on Sundays only; reverts to configured widget Mon–Sat. Time-aware, zero-touch. |

The whole feature is **pure-compute from the existing store** — no new table, no new
data source, no glasses involvement.

## Architecture

```
if config.sunday_review and today.weekday() == 6:   # Sunday
    review.render(draw, box, {"review": build_review(...)})
else:
    <existing week / life / weekofyear / yearprogress dispatch>
```

Mon–Sat are unchanged. The override touches only the bottom-left zone.

New files, mirroring existing patterns:

- **`app/review.py`** — *pure core* (sibling to `agenda.py` / `weatherview.py`).
  `build_review(habits, tasks_done_count, goals, today) -> {"wins", "misses", "rocks"}`.
  No I/O, no store import → fully unit-testable.
- **`app/widgets/review.py`** — `render(draw, box, ctx)` that draws the view
  (sibling to `today.py`, `habits.py`, etc.).

Data, all from the existing store:

- `habits` — already available via `store.get_habits()` (done/target/streak per habit).
- **One new store helper** — `store.get_tasks_done_this_week()`: count of `task`
  rows with `status='done'` and `done_at >= Monday`. (`done_at` already exists;
  `get_tasks()` simply doesn't expose it.)
- `goals` — `store.get_goals()` (text, progress, due).

`renderer` computes the view and passes it to the widget — the same
"renderer assembles data, widget draws" split used throughout.

## Compute rules

**Wins / misses (habits + tasks):**

- Each habit with a `target_per_week`: `done >= target` → **win** (`"Gym 5/5"`);
  `done < target` → **miss** (`"Read 2/5"`). Habits with no target are skipped
  (no pass/fail signal).
- Tasks: append `"N tasks done"` to wins when `N > 0`.
- Goal-progress deltas are **out of scope** — no historical snapshots exist
  (would need a new table; YAGNI).
- Cap **top 3 wins** and **top 3 misses** to fit the zone. Order misses by largest
  shortfall (`target - done`); order wins by highest ratio / longest streak.

**Next-week focus (goals):** rank by **soonest due first** (ascending `due`), then
goals without a due date by **lowest progress**; take **top 3**. Format
`"Ship side project (60%)"`, or `"Trip planning (due 18d)"` when a due date exists.

## Layout

Bottom-left zone (≈ half-width × ~42% height):

```
★ THIS WEEK
  Wins:   Gym 5/5  Water 7/7  8 tasks
  Misses: Read 2/5  Meditate 1/4
  ─────────────────────────────
  NEXT WEEK — focus
  1. Ship side project (60%)
  2. Trip planning (due 18d)
  3. ...
```

- The star is a **drawn INK primitive** (font-safe, like the weather glyphs and
  the Now/Next dot) — no emoji on e-ink.
- Long habit/goal text truncated with the existing `_truncate` helper.

## Edge cases

- **0 goals** → focus shows a calm prompt (`"Set goals to see focus"`).
- **<3 goals** → show what exists.
- **No targeted habits / no wins / no misses** → show `"—"` rather than an empty block.
- **Overflow** → truncate + the top-N caps above.
- **Day rollover into Sunday** is picked up by the existing background-poller
  re-render; `render_if_changed()` bumps the version naturally (no special
  midnight trigger needed).

## Testing

`tests/test_review.py` (pure, no rendering):

- Wins/misses correctness (done vs target; tasks-done line).
- Cap behavior (more than 3 wins / misses).
- Goal ranking (due-date order, then progress; due-days formatting).
- Empty-data fallbacks: no goals, no targeted habits, no tasks done, <3 goals.

## Out of scope

- Hand-set "big rocks" via the notebook/glasses capture pipeline (would reuse the
  `add_to_review()` TODO in `store.py`) — deferred.
- Goal-progress-delta wins (needs progress history snapshots).
- Configurable review day / full-body Sunday layout — deferred.
