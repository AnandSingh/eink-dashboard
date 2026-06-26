"""Unit tests for the pure weekly-review builder — no rendering, frozen `today`."""
import datetime as dt

from app import review

TODAY = dt.date(2026, 6, 28)  # a Sunday


def habit(name, done, target, streak=0):
    # `week` shape mirrors store.get_habits(); build_review only uses done/target/name.
    return {"name": name, "week": [None] * 7, "done": done, "target": target, "streak": streak}


def goal(gid, text, progress, due=None):
    return {"id": gid, "text": text, "progress": progress, "due": due}


# --- wins / misses ------------------------------------------------------


def test_wins_and_misses_split_on_target():
    habits = [habit("Gym", 5, 5), habit("Read", 2, 5), habit("Water", 7, 7)]
    r = review.build_review(habits, 8, [], TODAY)
    assert r["wins"] == ["Gym 5/5", "Water 7/7", "8 tasks done"]
    assert r["misses"] == ["Read 2/5"]


def test_tasks_line_omitted_when_zero():
    r = review.build_review([habit("Gym", 5, 5)], 0, [], TODAY)
    assert r["wins"] == ["Gym 5/5"]


def test_habit_without_target_is_skipped():
    habits = [habit("Floss", 3, None), habit("Zero", 1, 0)]
    r = review.build_review(habits, 0, [], TODAY)
    assert r["wins"] == []
    assert r["misses"] == []


def test_misses_ordered_by_largest_shortfall():
    habits = [habit("Meditate", 3, 4), habit("Read", 1, 5)]
    r = review.build_review(habits, 0, [], TODAY)
    assert r["misses"] == ["Read 1/5", "Meditate 3/4"]  # shortfall 4 before 1


def test_wins_capped_at_three_items():
    habits = [habit("A", 1, 1), habit("B", 1, 1), habit("C", 1, 1), habit("D", 1, 1)]
    r = review.build_review(habits, 5, [], TODAY)
    assert len(r["wins"]) == 3
    assert "5 tasks done" not in r["wins"]  # 3 habit wins fill the line first


# --- next-week focus (goals) -------------------------------------------


def test_goals_dated_before_undated_and_due_ascending():
    goals = [
        goal(1, "Ship", 0.6, None),
        goal(2, "Trip", 0.25, (TODAY + dt.timedelta(days=18)).isoformat()),
        goal(3, "Taxes", 0.1, (TODAY - dt.timedelta(days=3)).isoformat()),
        goal(4, "Piano", 0.4, TODAY.isoformat()),
    ]
    r = review.build_review([], 0, goals, TODAY)
    assert r["rocks"] == ["Taxes (overdue)", "Piano (due today)", "Trip (due 18d)"]


def test_undated_goals_ordered_by_lowest_progress():
    goals = [goal(1, "Big", 0.8), goal(2, "Small", 0.1)]
    r = review.build_review([], 0, goals, TODAY)
    assert r["rocks"] == ["Small (10%)", "Big (80%)"]


def test_unparseable_due_falls_back_to_progress():
    r = review.build_review([], 0, [goal(1, "Vague", 0.3, "someday")], TODAY)
    assert r["rocks"] == ["Vague (30%)"]


def test_no_goals_yields_empty_rocks():
    r = review.build_review([], 0, [], TODAY)
    assert r["rocks"] == []


def test_fewer_than_three_goals():
    goals = [goal(1, "One", 0.5), goal(2, "Two", 0.2)]
    r = review.build_review([], 0, goals, TODAY)
    assert len(r["rocks"]) == 2
