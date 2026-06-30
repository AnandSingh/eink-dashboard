# Phase 12: Habit Consistency Dots + Goal Countdown — Design (v3)

**Date:** 2026-06-30
**Status:** Designed (approved round 2)
**Author:** Anand (with Claude)

## Changes from v1

| # | Issue | What changed |
|---|-------|-------------|
| C1 | Partial-week evaluation would almost always show "missed" for the current week | Excluded the current week entirely. 4 dots = 4 *completed* weeks. The 7-day grid already covers the current week at daily granularity. |
| C2 | Streak logic duplicated between `get_habit_consistency()` and `get_habits()` | Removed `streak` from `get_habit_consistency()` return. The widget reads streaks from the existing `habit_data` dict (already passed), keyed by habit name. |
| C3 | `today` not passed to month widget in the renderer integration section | Consolidated all renderer changes into a single section showing both the consistency and `today` additions together. |
| S1 | Trend calculation noisy with only 4 weeks (2 vs 2 split) | Dropped trend arrow for now. Will add when window expands to 12 weeks. |
| S2 | "CONSISTENCY" header adds visual clutter (third titled section in zone) | Removed the header. Dots section separated from streak line by vertical spacing only — self-explanatory. |
| S5 | Vertical space with 5+ habits — what happens when it doesn't fit? | Consistency section hides entirely if remaining height < 120px. |

## Changes from v2

| # | Issue | What changed |
|---|-------|-------------|
| R2-C1 | Year-boundary ordering bug — grouping by ISO week number gives wrong order across Dec→Jan | Iterate over computed Monday dates instead of grouping by ISO week number. Count log entries per `[monday, monday+7d)` slot. Order-stable regardless of year boundaries. |
| R2-C2 | Fixed 120px threshold overflows with 5-6 habits — needed space is `N_rows * row_height` | Dynamic height check: `remaining >= n_consistency * _CONS_LINE + 16`. Section hides if it won't fully fit. |
| R2-S3 | Streak displayed twice — in STREAK line and in consistency row | Dropped streak from consistency row. Dots show only `name ●●●○ 75%`. STREAK line above already covers it. |

## Goal

Two additions to the dashboard:

1. **Habit consistency dots** — a new section below the existing 7-day habit grid
   showing per-habit weekly target hit/miss over the last 4 completed weeks, with
   hit rate and streak.
2. **Goal countdown format** — replace the raw `due 07-12` text in the Month widget
   with a glanceable `12d left` / `due today` / `3d overdue` format.

## Scope changes from original plan

| Original item | Decision | Why |
|---------------|----------|-----|
| Streak board | Dropped | Already shown in the existing habits widget + now in consistency row |
| Goal→habit linkage | Dropped | YAGNI — habits and goals are fundamentally different; the visual proximity on the dashboard is sufficient |

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Consistency visualization | Dots (●/○) per week, not heatmap grid | Compact, complementary to the 7-day grid (micro vs macro), fits below existing widget |
| Dot style | Filled circle (●) = hit target, outlined (○) = missed | Consistent with the existing habit grid's filled/outlined squares |
| Time window | 4 completed weeks (excludes current week) | Start small; current week already covered by 7-day grid. Expandable to 12 by changing a constant. |
| Trend arrow | Omitted at 4 weeks | Only 2 data points per half — too noisy. Will add at 12 weeks. |
| Section header | No header — separated by spacing only | Zone already has "HABITS" and "STREAK" headers; a third adds clutter. |
| Placement | Below the streak line in the Habits widget | Enhances, doesn't replace — micro (daily) + macro (weekly) views |
| Goal countdown | Replace `due MM-DD` with `Nd left` / `due today` / `Nd overdue` | More glanceable; raw date is less useful at a glance |
| Overflow | Consistency section hides if it won't fully fit (dynamic height check) | Graceful degradation with many habits |

## Architecture

### A. Habit consistency dots

#### `store.py` — new query function

```python
def get_habit_consistency(weeks: int = 4) -> list[dict]:
    """Return per-habit weekly target hit/miss for the last N completed weeks.

    Excludes the current (incomplete) week — the 7-day grid covers it.

    Each entry: {
        "name":     str,
        "weeks":    [bool] * N,   # oldest → newest; True = hit target that week
        "hit_rate": int,          # percentage of weeks where target was hit (0–100)
    }
    """
```

**Algorithm:**
1. Compute the Monday of the current week (`this_monday`). The scan window is
   the N weeks *before* this Monday (i.e., completed weeks only).
   `oldest_monday = this_monday - timedelta(weeks=N)`.
2. Build a list of N Monday dates: `[oldest_monday, oldest_monday + 7d, …]`.
   This avoids ISO week number grouping (which breaks at year boundaries).
3. For each habit with a non-null `target_per_week`:
   a. Query `habit_log` rows where `date >= oldest_monday` and `date < this_monday`
      — a single bounded query per habit, using one shared connection.
   b. For each Monday slot, count log entries whose date falls in `[monday, monday+7d)`.
   c. `hit = count >= target_per_week` for each week.
4. `hit_rate = round(sum(weeks) / len(weeks) * 100)`.
5. Habits without `target_per_week` are skipped.

**Note:** Streak is **not** computed here. The widget reads it from the existing
`habit_data` dict (passed separately), keyed by habit name.

#### `widgets/habits.py` — add consistency section

Below the existing streak line, add (no header — spacing only):

```
Gym    ●●●○  75%
Read   ●●○○  50%
Water  ●●●●  100%
```

No streak in this row — the STREAK line above already shows it.

**Drawing details:**
- Section only renders if remaining vertical space fits all consistency rows:
  `remaining >= n_rows * 36 + 16` (36px per row + 16px top padding).
  If it doesn't fit, the section is hidden entirely.
- Dots are `draw.ellipse()` — 8px diameter, filled (`theme.INK`) or outlined
  (`theme.FAINT`, width=2). Same primitive style as the habit grid squares.
- Hit rate right-aligned after dots.

**Data flow in the widget:**
```python
def render(draw, box, data) -> None:
    """data = {
        "habits": [{"name", "week", "done", "target", "streak"}],
        "consistency": [{"name", "weeks": [bool], "hit_rate": int}],
    }"""
```

#### Layout math (verified):

Row height for consistency: 36px. Top padding: 16px.

| Habit count | Grid+streak height | Remaining (of 605px) | Needed | Fits? |
|-------------|-------------------|----------------------|--------|-------|
| 3 | 28+238+34=300 | 305 | 3×36+16=124 | ✅ |
| 4 | 28+296+34=358 | 247 | 4×36+16=160 | ✅ |
| 5 | 28+354+34=416 | 189 | 5×36+16=196 | ❌ hidden |
| 6 | 28+412+34=474 | 131 | 6×36+16=232 | ❌ hidden |

### B. Goal countdown format

#### `widgets/month.py` — format change

Replace the due date display logic (line 23-26). The widget receives
`{"goals": goals, "today": today_date}`.

```python
import datetime as dt

# In render(), replace the due date block:
if goal.get("due"):
    try:
        due = dt.date.fromisoformat(goal["due"])
        diff = (due - data["today"]).days
        if diff > 0:
            due_txt = f"{diff}d left"
        elif diff == 0:
            due_txt = "due today"
        else:
            due_txt = f"{-diff}d overdue"
    except (ValueError, TypeError):
        due_txt = f"due {goal['due']}"  # fallback to raw text
    tw = draw.textlength(due_txt, font=df)
    draw.text((x + w - pad - tw, ty + 4), due_txt, font=df, fill=theme.MUTED)
```

### Renderer — all changes (consolidated)

In `_render_unlocked()`, two changes:

```python
# 1. Pass consistency data to habits widget (after existing habit_data line)
consistency = store.get_habit_consistency()
habits.render(draw, zones["habits"], {"habits": habit_data, "consistency": consistency})

# 2. Pass today to month widget (replaces existing call)
month.render(draw, zones["month"], {"goals": goals, "today": today_date})
```

### Tests

#### `tests/test_habit_consistency.py`

- **Known data**: seed habit + habit_log with specific dates, verify
  `get_habit_consistency()` returns correct `weeks`, `hit_rate`.
- **No target**: habit without `target_per_week` is excluded from results.
- **Current week excluded**: log entries from the current week do not affect the
  4-week dots.
- **Empty log**: habit with no log entries returns all-miss weeks (4× False).
- **All hit**: habit that hit target every week returns all-True + 100%.

#### `tests/test_goal_countdown.py`

- **Future due**: `12d left` format.
- **Today**: `due today`.
- **Past due**: `3d overdue`.
- **No due date**: no countdown text shown.
- **Unparseable due**: falls back to `due <raw>`.

## Files changed / created

| File | Action |
|------|--------|
| `server/app/store.py` | Edit — add `get_habit_consistency()` |
| `server/app/widgets/habits.py` | Edit — add consistency dots section |
| `server/app/widgets/month.py` | Edit — add `import datetime as dt`, replace due date with countdown |
| `server/app/renderer.py` | Edit — pass consistency data to habits + today to month widget |
| `server/tests/test_habit_consistency.py` | Create |
| `server/tests/test_goal_countdown.py` | Create |
| `docs/ROADMAP.md` | Edit — move items to Done |

## Out of scope

- Streak board (already in habits widget).
- Goal→habit linkage (YAGNI).
- Trend arrow (add when window expands to 12 weeks).
- Expanding to 12 weeks (future — just change the `weeks` constant).
- Habit/goal CRUD API (managed via seed_demo / direct SQL for now).
