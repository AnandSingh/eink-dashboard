VERDICT: NEEDS_REVISION

## Summary Assessment

The architecture is sound and faithfully mirrors the existing pure-core / widget split, and the layout comfortably fits (the "#1 risk" is a non-issue at this resolution). However, there is a real correctness gap — **nothing re-renders on a time cadence when calendar and weather are both disabled, so the dashboard may never flip into (or out of) Sunday mode** — plus several under-specified data/formatting assumptions that will produce wrong output or crashes.

## Critical Issues (must fix)

### 1. Day-rollover into/out of Sunday is NOT reliably picked up (real gap)
The design claims (Edge cases, line 98-100): *"Day rollover into Sunday is picked up by the existing background-poller re-render."* This is only true if a poller is actually running. I traced every re-render path:

- `glasses/router.py:41` and `glasses/bot.py:37` — render only on a **new photo / bot message** (event-driven, not time-driven). `glasses/watcher.py` polls the inbox but never calls render.
- `calendar/sync.py:_loop` — re-renders every `render_tick`, but `start_background()` is a **no-op if `CALENDAR_ICS_URL` is unset** (sync.py:62-64).
- `weather/sync.py:_loop` — re-renders on each successful poll, but `start_background()` is a **no-op if `WEATHER_ENABLED=false`** (sync.py:48-50).
- `api.py` — renders once at startup; `/dashboard.png` only renders if the file is missing; `/version` never renders. The Pi client (`pi-client/display.py`) only polls `/version` and never triggers a server render.

So if a user runs the core dashboard with calendar **and** weather both disabled (a supported configuration — both are opt-in, and `WEATHER_ENABLED` defaults true but is explicitly toggleable), the **only** things that re-render are photo/bot events. On a quiet Saturday night with no glasses activity, the screen will sit on Saturday's render straight through Sunday and into Monday. The feature simply won't activate. Even with weather on (default), activation is quantized to the 30-min weather poll *and* gated by `render_if_changed` — which is fine — but the **all-pollers-off** case is a genuine silent failure.

This needs an explicit decision in the design, not a hand-wave. Options: (a) add a lightweight always-on "midnight/daily tick" daemon in the core that calls `render_if_changed()` (most robust; also fixes the pre-existing bug that the date in the header never advances without a poller); (b) document that `SUNDAY_REVIEW` requires at least one poller enabled and warn if not; (c) have the Pi client send a daily nudge. Option (a) is the right fix and is small.

### 2. `build_review` signature omits the data it needs for ranking/formatting
The proposed core signature is `build_review(habits, tasks_done_count, goals, today)`. But the compute rules require:
- **Goal due-date ranking** ("soonest due first") and **"due 18d"** formatting — both require comparing `due` against `today`. `today` is passed, good. But note `month.py:24` formats due as a literal `"due " + goal["due"][5:]` (MM-DD slice) — there is **no existing "Nd" relative-days helper**; this is net-new date math that must handle `due` being `None`, past, today, or unparseable (`get_goals()` returns `due` straight from SQLite as a raw string or `None`). The design says "due 18d" but never specifies behavior for past/today/None. Specify: e.g. `None` → fall back to `(progress%)`; past → `"overdue"` or `"due -3d"`; today → `"due today"`. Also state the parse-failure fallback (mirror `renderer._parse_date`, which returns `None` on bad input).

### 3. Goal ranking with mixed due/no-due and ties is under-defined
The rule "rank by soonest due first, then goals without a due date by lowest progress" is ambiguous about **how the two groups interleave**. As written it implies: all due-dated goals (ascending due) come first, then all undated goals (ascending progress). State that explicitly, and define tie-breakers: equal due dates → by `id`/insertion order (stable); equal progress → by `id`. Without a stable final key the top-3 cut is nondeterministic across renders, which on e-ink means spurious refreshes (the `render_if_changed` hash flips). Recommend appending `id` as a final sort key — but note `get_goals()` does **not currently select `id`** (store.py:204), so either add it to the query or rely on Python's stable sort over the existing insertion order returned by `ORDER BY id`.

### 4. `get_tasks_done_this_week()` "this week" boundary + timezone must match habits
The design says count `task` rows with `status='done'` and `done_at >= Monday`. Two concrete hazards:
- **`done_at` is naive local time.** `mark_task_done` stores `dt.datetime.now().isoformat()` (store.py:295) — no tz. `get_habits()` computes its week with `dt.date.today()` and `today.weekday()` (also naive local). These agree *only* because both are naive-local; the design must state the query uses the **same naive-local Monday** (`date.today() - timedelta(days=weekday())`) and compares `done_at >= monday.isoformat()`. A lexicographic string compare on ISO timestamps works **only** if you compare against a date-prefixed string and `done_at` is always full ISO — confirm and prefer `done_at >= '<monday>T00:00:00'` or `date(done_at) >= :monday` to avoid the `'2026-06-22'` vs `'2026-06-22T...'` boundary subtlety.
- The "this week" used for tasks must be the **same Monday** the habit grid uses, or the "wins" line will mix windows. Call this out and ideally compute Monday once in the renderer and pass it down, rather than recomputing in two places.

## Suggestions (nice to have)

- **Layout fits — drop the stated "#1 risk" worry.** I measured it. The bottom-left zone is **1280 x 605 px** (`_zones()`: header 144, footer 86, body 1210, row 605, col 1280). Usable text width ≈ 1224px. Measured widths at font 32 (DejaVu, the shipped font): `"Wins: Gym 5/5 Water 7/7 8 tasks"` = 566px, `"Misses: Read 2/5 Meditate 1/4"` = 492px, `"1. Q2 goal: ship side project (60%)"` = 555px — all well under 1224. Height budget: ~510px usable / ~44-56px per line (sibling `line_h` values) ≈ 9 lines, enough for header + wins + misses + rule + NEXT WEEK + 3 focus. **Width truncation via `_truncate` is barely needed** except for pathological long goal text. Update the design to say layout is comfortable rather than tight.
- **Mockup vs. compute-rules inconsistency.** The Layout mockup (lines 78-86) shows wins and misses each as a *single wrapped line* ("Wins: Gym 5/5 Water 7/7 8 tasks"), but the compute rules (line 67) say "top 3 wins and top 3 misses." Decide: are wins/misses rendered as one compact line each (with up to 3 items inline) or as up to 3 separate lines each? This changes both the line budget and the widget draw loop. Make the mockup and the rules agree.
- **`_truncate` lives in `renderer.py`, not a shared util.** The design says the widget uses "the existing `_truncate` helper" (line 90). It's `renderer._truncate` (renderer.py:135) — a private module function. A widget importing `from ..renderer import _truncate` creates a widget→renderer back-import (renderer imports widgets, so this risks a cycle). Cleaner: move `_truncate` to `theme.py` or a small `widgets/_util.py`, or have the widget do its own truncation. Minor, but flag it so the implementer doesn't create an import cycle.
- **`tasks_done_count` shape.** Wins says append `"N tasks done"` when `N>0`, but the mockup shows `"8 tasks"`. Pick one string. Trivial, but tests will assert on it.
- **`weekday()==6` is correct for Sunday** (Mon=0..Sun=6), and matches `get_habits()`'s own `today.weekday()` convention. Good. Just make sure the renderer evaluates `today.weekday()` from the same `dt.date.today()` it already computes at renderer.py:237 (pass it in, don't recompute).
- **Empty/None habit target:** `get_habits()` returns `target` straight from the column, which is **nullable** (schema line 25, `target_per_week INTEGER` with no default). The "skip habits with no target" rule is correct and necessary — confirm the implementation treats `target is None` (not `target == 0`) as "skip", and guards division for the win "highest ratio" ordering (`done/target` with `target` possibly 0 if someone sets 0).

## Verified Claims (things you confirmed are correct)

- **Pure-core sibling pattern is real.** `agenda.py` and `weatherview.py` are exactly the "no I/O, no store import, fully unit-testable" core helpers the design cites; `tests/test_agenda.py` exercises `agenda.banner_text` with a frozen clock and no network — a clean template for `tests/test_review.py`.
- **Widget `render(draw, box, ctx)` signature is real and uniform** across `today.py`, `habits.py`, `month.py`, `week.py`, `extras.py`. A new `widgets/review.py` fits the dispatch in `_render_bottom_left` (renderer.py:150-164) cleanly.
- **`get_habits()` returns `done` and `target`** as the design assumes (store.py:189-197: keys `name, week, done, target, streak`). `done` = count of True slots in the Mon..Sun week; `target` = `target_per_week` (nullable).
- **`task` table has `done_at`** (schema line 19) and it is set by `mark_task_done` (store.py:295). `get_tasks()` indeed does not expose it (store.py:153), so a new helper is warranted — feasible as claimed.
- **`get_goals()` returns `text, progress, due`** (store.py:202-207). `progress` is a 0..1 float; `due` is a raw ISO date string or `None`.
- **`_truncate` exists** (renderer.py:135) and works as described (ellipsis trim by width). Caveat in Suggestions about its location.
- **`SUNDAY_REVIEW` config pattern is straightforward** — it would slot into `Config` exactly like `weather_enabled` (config.py:39): `sunday_review: bool = os.getenv("SUNDAY_REVIEW","true").lower() != "false"`.
- **The "renderer assembles data, widget draws" split** is exactly how the renderer already works (renderer.py:240-247 fetches habits/tasks/goals and passes dicts to widgets).
</content>
</invoke>
