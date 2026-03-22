"""
Automated test suite for PawPal+ core logic.

Run with:  python -m pytest
"""

from datetime import date, timedelta
import pytest

from pawpal_system import Task, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_owner():
    """Owner with two pets and several tasks."""
    owner = Owner(name="Jordan")

    dog = Pet(name="Mochi", species="dog")
    dog.add_task(Task("Afternoon walk", "14:00", 30, "medium", "daily"))
    dog.add_task(Task("Morning walk",   "07:00", 20, "high",   "daily"))
    dog.add_task(Task("Heartworm pill", "08:00", 5,  "high",   "weekly"))

    cat = Pet(name="Whiskers", species="cat")
    cat.add_task(Task("Morning feed",  "07:30", 10, "high",  "daily"))
    cat.add_task(Task("Litter clean",  "09:00", 10, "medium","daily"))

    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner


@pytest.fixture
def scheduler(basic_owner):
    return Scheduler(basic_owner)


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_task_mark_complete_changes_status():
    """mark_complete() must flip completed to True."""
    task = Task("Morning walk", "07:00", 20, "high", "once")
    assert not task.completed
    task.mark_complete()
    assert task.completed


def test_daily_task_recurrence_creates_next_day():
    """A daily task should return a new task due the following day."""
    today = date.today()
    task = Task("Morning walk", "07:00", 20, "high", "daily", due_date=today)
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert not next_task.completed


def test_weekly_task_recurrence_creates_next_week():
    """A weekly task should return a new task due 7 days later."""
    today = date.today()
    task = Task("Heartworm pill", "08:00", 5, "high", "weekly", due_date=today)
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_once_task_returns_no_recurrence():
    """A 'once' task should not produce a follow-up task."""
    task = Task("Vet visit", "10:00", 60, "high", "once")
    next_task = task.mark_complete()
    assert next_task is None


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increases_count():
    """Adding a task must increase the pet's task count by one."""
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk", "07:00", 20, "high", "daily"))
    assert len(pet.tasks) == 1


def test_remove_task_decreases_count():
    """remove_task() should delete the matching task and return True."""
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(Task("Walk", "07:00", 20, "high", "daily"))
    result = pet.remove_task("Walk")
    assert result is True
    assert len(pet.tasks) == 0


def test_remove_nonexistent_task_returns_false():
    """Removing a task that doesn't exist should return False."""
    pet = Pet(name="Mochi", species="dog")
    assert pet.remove_task("Ghost task") is False


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_owner_get_all_tasks_returns_all(basic_owner):
    """get_all_tasks() should return tasks from every pet."""
    all_tasks = basic_owner.get_all_tasks()
    assert len(all_tasks) == 5  # 3 dog + 2 cat


def test_owner_add_pet(basic_owner):
    """Adding a new pet should increase the owner's pet count."""
    before = len(basic_owner.pets)
    basic_owner.add_pet(Pet(name="Goldie", species="fish"))
    assert len(basic_owner.pets) == before + 1


# ---------------------------------------------------------------------------
# Scheduler — sorting
# ---------------------------------------------------------------------------

def test_sort_by_time_is_chronological(scheduler):
    """sort_by_time() must return tasks in ascending HH:MM order."""
    sorted_tasks = scheduler.sort_by_time()
    times = [t.time for _, t in sorted_tasks]
    assert times == sorted(times)


# ---------------------------------------------------------------------------
# Scheduler — filtering
# ---------------------------------------------------------------------------

def test_filter_by_pet_returns_correct_pet(scheduler):
    """filter_by_pet() must only return tasks belonging to that pet."""
    mochi_tasks = scheduler.filter_by_pet("Mochi")
    assert all(pn == "Mochi" for pn, _ in mochi_tasks)


def test_filter_by_status_incomplete(scheduler):
    """filter_by_status(False) returns only incomplete tasks."""
    incomplete = scheduler.filter_by_status(False)
    assert all(not t.completed for _, t in incomplete)


# ---------------------------------------------------------------------------
# Scheduler — conflict detection
# ---------------------------------------------------------------------------

def test_conflict_detection_flags_same_time():
    """detect_conflicts() should flag two tasks for the same pet at the same time."""
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "dog")
    pet.add_task(Task("Task A", "09:00", 10, "high",   "once"))
    pet.add_task(Task("Task B", "09:00", 5,  "medium", "once"))
    owner.add_pet(pet)
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1
    assert "09:00" in warnings[0]


def test_no_conflict_when_times_differ():
    """No warning should be produced when task times are all different."""
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "dog")
    pet.add_task(Task("Task A", "08:00", 10, "high",   "once"))
    pet.add_task(Task("Task B", "09:00", 5,  "medium", "once"))
    owner.add_pet(pet)
    warnings = Scheduler(owner).detect_conflicts()
    assert warnings == []


# ---------------------------------------------------------------------------
# Scheduler — recurrence via mark_task_complete
# ---------------------------------------------------------------------------

def test_scheduler_marks_complete_and_adds_recurrence(basic_owner):
    """mark_task_complete should complete the task and append the next daily one."""
    dog = basic_owner.pets[0]  # Mochi
    before_count = len(dog.tasks)
    sched = Scheduler(basic_owner)
    result = sched.mark_task_complete("Mochi", "Morning walk")
    assert result is True
    assert dog.tasks[1].completed  # original task
    # A new task for tomorrow was appended
    assert len(dog.tasks) == before_count + 1


def test_scheduler_mark_complete_returns_false_for_unknown(scheduler):
    """Attempting to complete a nonexistent task should return False."""
    assert scheduler.mark_task_complete("Mochi", "Nonexistent task") is False


# ---------------------------------------------------------------------------
# Scheduler — generate_schedule
# ---------------------------------------------------------------------------

def test_generate_schedule_high_priority_first(basic_owner):
    """High-priority tasks should come before medium/low ones in the schedule."""
    sched = Scheduler(basic_owner)
    schedule = sched.generate_schedule()
    priorities = [t.priority for _, t in schedule]
    order = [{"high": 0, "medium": 1, "low": 2}[p] for p in priorities]
    assert order == sorted(order)
