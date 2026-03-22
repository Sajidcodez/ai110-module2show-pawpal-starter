# PawPal+ Project Reflection

## System Design

Three core actions a user should be able to perform:
1. Add a pet — register a pet (name, species, breed) under an owner account.
2. Schedule a task — create a timed, prioritized care activity for a specific pet.
3. View today's schedule — see all pending tasks sorted by priority and time, with conflict warnings.

---

## 1. System Design

**a. Initial design**

I designed four classes with clearly separated responsibilities:

- **Task** — a Python dataclass representing one care activity. Attributes: `title`, `time` (HH:MM), `duration_minutes`, `priority`, `frequency`, `description`, `completed`, and `due_date`. Its only behaviour is `mark_complete()`, which returns the next recurrence task or `None`.
- **Pet** — a dataclass holding the pet's profile (`name`, `species`, `breed`) and a list of `Task` objects. Responsible for task membership (`add_task`, `remove_task`).
- **Owner** — a dataclass holding the owner's name and a list of `Pet` objects. Provides `get_all_tasks()` as a flat view across all pets.
- **Scheduler** — a plain class (not a dataclass) that takes an `Owner` and implements all algorithmic logic: sorting, filtering, conflict detection, recurrence handling, and schedule generation.

This kept data (Task, Pet, Owner) separate from logic (Scheduler), which made both easier to test independently.

**b. Design changes**

During implementation I realised the original skeleton had `Scheduler.sort_by_time()` operate only on today's tasks. I added an optional `tasks` parameter so callers (including tests) can pass any task list to sort — making the method more reusable without breaking its default behaviour. I also added `generate_schedule()` as a higher-level method that combines priority ordering and time ordering in one step, which the UI needed to produce a meaningful plan.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:
- **Priority** (`high` > `medium` > `low`) — the primary sort key in `generate_schedule()`.
- **Time of day** — the secondary sort key, so equally-prioritised tasks appear in chronological order.
- **Due date** — only tasks with `due_date <= today` appear in the daily schedule.
- **Completion status** — completed tasks are excluded from the daily view.

Priority was weighted most heavily because a missed medication is more serious than a missed grooming session

**b. Tradeoffs**

The conflict detector only flags tasks for the same pets at the exact same time (string equality on `HH:MM`). It does not check overlapping durations — for example, a 30-minute walk at 07:00 and a 10-minute feed at 07:15 would not be flagged as a conflict. That is a problem as you can't simulatenously do both unless your pet is superanimal. I would say this is a reasonable tradeoff for a daily planner because pet care tasks are rarely performed simultaneously by the same person, and exact time collisions (a real scheduling mistake) are the most actionable warning to surface. Overlap detection would require more complex interval arithmetic and could produce noisy false positives for tasks the owner intentionally interleaves.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude Code as the primary AI tool throughout this project:
- **Design brainstorming** — asked it to suggest which algorithmic features (sorting, filtering, conflict detection, recurrence) would be most useful for a pet scheduler.
- **Code generation** — used it to scaffold the class stubs, flesh out method implementations, and write the full test suite.
- **Debugging** — when the `generate_schedule()` sort key needed to handle both priority and time, I asked it to explain Python's tuple-sort behaviour to confirm the approach.
- **UI wiring** — asked it to explain `st.session_state` and how to make an `Owner` object persist across Streamlit reruns.

The most useful prompt pattern was providing context (`"Here is my pawpal_system.py"`) and asking a focused question rather than open-ended `"write everything or do everything for me"` requests.

**b. Judgment and verification**

An early AI suggestion generated a `Scheduler.get_todays_tasks()` method that compared `task.due_date == date.today()` (exact equality). I changed this to `task.due_date <= date.today()` because overdue tasks should still appear in the daily schedule — a pet's missed medication from yesterday is still urgent. I verified the fix by adding a test with a past due date and confirming it appeared in the output.

---

## 4. Testing and Verification

**a. What I tested**

The test suite covers 17 behaviours across all four classes:

- **Task** — `mark_complete()` sets `completed = True`; daily/weekly recurrence returns a correctly dated next task; `once` tasks return `None`.
- **Pet** — adding a task increases count; removing a task decreases count; removing a nonexistent task returns `False`.
- **Owner** — `get_all_tasks()` aggregates tasks from all pets; `add_pet()` grows the pets list.
- **Scheduler** — chronological sort correctness; pet and status filtering; conflict detection for same/different times; recurrence via `mark_task_complete`; priority ordering in `generate_schedule()`.

These tests matter because the scheduler's correctness depends on all four classes interacting correctly. A bug in `mark_complete()` would silently break recurring tasks everywhere.

**b. Confidence**

All 17 tests pass. Edge cases I would test next given more time:
- A pet with zero tasks (empty schedule should not crash).
- Tasks with `due_date` in the future (should not appear today).
- Marking the same task complete twice (should be a no-op the second time).
- Cross-pet conflicts (currently only same-pet conflicts are detected).

---

## 5. Reflection

**a. What went well**

The "CLI-first" workflow paid off. Having a working `main.py` that I could run in the terminal gave me confidence in the backend logic before touching the UI. When the Streamlit wiring needed changes, I never had to question whether the underlying classes were broken.

**b. What you would improve**

I would add a persistent data layer (e.g., JSON file or SQLite) so that tasks survive a browser refresh. Right now, all data lives in `st.session_state`, which resets if the server restarts. I would also extend conflict detection to check for overlapping durations, not just identical start times.

**c. Key takeaway**

The most important lesson was that AI is a powerful "accelerator" but a poor "architect". It can generate correct code quickly, but it cannot know which tradeoffs matter for your specific scenario (like "overdue tasks should still appear today"). Being the lead architect means making those judgment calls explicitly, testing them, and documenting why and not just accepting whatever the AI produces.
