VERDICT: NEEDS_REVISION

## Summary Assessment

The rev-2 revision genuinely fixes three of the four round-1 critical issues (due formatting, goal-ranking determinism, task week boundary) and the `_truncate` move is correct and cycle-free. But the headline fix — the daily-tick daemon — is specified to start "unconditionally from `api.py` startup," which contradicts how this codebase actually wires its always-on threads: calendar and weather sync are started from `main.py`'s `_start_integrations()` hook, not `api.py`. The design's own claim that the daemon is "started consistent with how weather/calendar sync are started there [api.py]" is factually wrong against the repo, and must be reconciled before build.

## Critical Issues (must fix)

### 1. Daemon start location contradicts the actual threading pattern (rev-1 fix #1 not faithfully grounded)
The design states (line 63, 92-93) the tick daemon is "Started unconditionally from `api.py` startup" and frames this as mirroring "how weather/calendar sync are started there." That is not how the repo works:

- `app/weather/sync.py:48` and `app/calendar/sync.py:60` expose `start_background()`, but those are **called from `app/main.py:27-29`** inside `_start_integrations()` (a second `@app.on_event("startup")` hook), **not from `api.py`**.
- `api.py`'s startup hook (`api.py:19-29`) does only DB init + first `render_if_changed()`. Its docstring and the `main.py` comment ("The core never imports glasses; the integration plugs in here") establish `api.py` = glasses-independent core, `main.py` = composition root where daemons are wired.
- The deployed entry point is `app.main` (`server/Dockerfile:18` → `CMD ["python", "-m", "app.main"]`), so `main.py`'s hook always runs.

This is not merely cosmetic: the design explicitly anchors the fix on a false statement about the existing pattern, which undermines the "I verified the pattern" basis the reviewer asked for. Two acceptable resolutions, pick one and state it:
  - (a) Start the daemon from `main.py:_start_integrations()` alongside `calendar_sync`/`weather_sync` (true mirror of the existing pattern), or
  - (b) Deliberately start it from `api.py` startup *because* the tick is core (unlike glasses/calendar/weather it has no feature gate), and say so explicitly — noting it is intentionally a different layer than the opt-in pollers, not a mirror of them.

Either works mechanically (both hooks run under `app.main`; `render_if_changed()` is lock-guarded and re-entrancy-safe, so no deadlock/double-start corruption even if it fires before `main.py`'s hook). But the design text as written is self-contradictory and names the wrong file. Fix the file reference and the "consistent with calendar/weather" justification.

Note also: if the daemon were ever relied upon under the bare `api.run()` path (api.py:51), only option (a)-from-main would fail there; option (b)-from-api would still work. This is a minor argument in favor of (b), but it must be a stated decision, not an unexamined claim.

## Suggestions (nice to have)

- **"Monday computed once" is slightly overstated.** Design change #4 says Monday is "computed once in the renderer and passed down." In reality `get_habits()` computes its own Monday internally (`store.py:165`) and never exposes it; only the new `get_tasks_done_this_week(monday)` receives the renderer's Monday. So Monday is computed in *two* places that are equal by construction (both `date.today() - timedelta(days=weekday())`, naive-local). That's fine and correct, but reword to "the task helper is passed the same naive-local Monday the habit grid derives" rather than implying a single shared computation — otherwise an implementer may go looking for a Monday return value from `get_habits()` that does not exist.

- **Pin where the Sunday branch lives.** The architecture pseudocode (lines 46-50) shows the `config.sunday_review and today.weekday()==6` check but doesn't say whether it wraps or lives inside `_render_bottom_left()` (renderer.py:150). Since that function already receives `today_date`, putting the check at its top is the clean spot and reuses the existing param (no recompute). Worth one sentence so the dispatch in renderer.py:246 stays the single call site.

- **`get_tasks_done_this_week` should mirror the `connect()`/Row pattern.** Trivial, but state it returns an `int` (the `COUNT(*)`), not a row/dict, so `build_review`'s `tasks_done_count` param is unambiguous for the test that asserts the `"N tasks done"` string.

## Verified Claims (things you confirmed are correct)

- **`due` formatting is now fully specified** (lines 116-120): future→`(due Nd)`, today→`(due today)`, past→`(overdue)`, None/unparseable→`(P%)`, with defensive parsing mirroring `renderer._parse_date` (renderer.py:143-147, which returns `None` on `ValueError`/`TypeError`). This closes rev-1 critical #2.

- **Goal ranking is now deterministic and `get_goals()`+`id` is coherent** (lines 78, 110-113). Two groups (dated asc by due then id; undated asc by progress then id), top 3, `id` as final tie-break. Adding `id` to the `SELECT` (store.py:205) does **not** break `month.py`: it reads goals by key (`goal["text"]`, `.get("due")`, `.get("progress")`) and never iterates keys or unpacks positionally, so an extra dict key is inert. Closes rev-1 critical #3.

- **Task week boundary mechanism works.** I tested `date(done_at) >= :monday` in SQLite against `done_at` values stored by `mark_task_done` (`store.py:295`, `dt.datetime.now().isoformat()`, e.g. `'2026-06-22T00:00:00.123456'`). With `monday='2026-06-22'`: a Monday-00:00 task counts, a Sunday-23:59 task does not — exactly the boundary the design's store test asserts (line 167-170). Both `get_habits()` and the proposed helper use naive-local `date.today()-weekday()`, so windows align. Closes rev-1 critical #4.

- **`_truncate` → `theme.py` is cycle-free and low-risk.** `theme.py` imports only `functools` and `PIL.ImageFont` (no store/renderer/widgets), so it cannot cycle. `_truncate` has exactly one current caller (`renderer.py:131`); the move + one import update is trivial. No widget currently imports renderer, confirming the design's stated cycle is preventive (the widget→renderer back-import would be new) rather than pre-existing. Sound.

- **The rollover gap the daemon addresses is real.** Confirmed every re-render path is event- or poll-gated: glasses (event), `calendar/sync.py:62` (no-op without `CALENDAR_ICS_URL`), `weather/sync.py:50` (no-op when `WEATHER_ENABLED=false`), and `api.py` renders only at startup / on missing PNG. With both pollers off, nothing advances the day. The daemon is the right fix.

- **`render_if_changed()` is safe at hourly cadence.** It holds `_RENDER_LOCK`, renders to a temp file + `os.replace` (atomic), hashes the PNG, and bumps `version`/`png_hash` only on a real pixel change (renderer.py:266-280). Hourly ticks on a quiet day cause zero e-ink refreshes, as claimed. No self-deadlock: public entry points hold the lock and call the unlocked core once.

- **Layout dimensions check out.** With the real defaults `PANEL_WIDTH=2560`/`PANEL_HEIGHT=1440` (config.py:15-16), `_zones()` yields col_w=1280, header=144, footer=86, body=1210, row=605 → bottom-left zone = 1280×605 as stated (lines 124-128). The rev-1 width measurements were against this real panel.

- **`weekday()==6` = Sunday** (Mon=0) and matches `get_habits()`'s own `today.weekday()` convention (store.py:165). Reusing the renderer's `today_date` (renderer.py:237) avoids a recompute, as the design says.

- **Habit target handling is correct.** `target_per_week` is nullable (schema line 25, no default); `get_habits()` returns it raw (store.py:195). The design's skip-on-`None` and guard-on-`0` rules (lines 99-102) prevent false misses and division errors for the win ratio ordering.
