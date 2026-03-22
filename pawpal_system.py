"""
PawPal+ — core logic layer.

Contains all backend classes: Task, Pet, Owner, and Scheduler.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """Represents a single pet care activity."""

    title: str
    time: str               # "HH:MM" 24-hour format
    duration_minutes: int
    priority: str           # "low" | "medium" | "high"
    frequency: str          # "once" | "daily" | "weekly"
    description: str = ""
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task complete and return the next recurrence, or None."""
        self.completed = True
        if self.frequency == "daily":
            return Task(
                title=self.title,
                time=self.time,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                frequency=self.frequency,
                description=self.description,
                completed=False,
                due_date=self.due_date + timedelta(days=1),
            )
        if self.frequency == "weekly":
            return Task(
                title=self.title,
                time=self.time,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                frequency=self.frequency,
                description=self.description,
                completed=False,
                due_date=self.due_date + timedelta(weeks=1),
            )
        return None


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Stores pet details and its associated task list."""

    name: str
    species: str
    breed: str = ""
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task_title: str) -> bool:
        """Remove the first task matching task_title; return True if found."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.title != task_title]
        return len(self.tasks) < original_len


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Manages one or more pets for a single user."""

    name: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List[Tuple[str, Task]]:
        """Return (pet_name, task) pairs for every task across all pets."""
        return [(pet.name, task) for pet in self.pets for task in pet.tasks]


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """The 'brain' that retrieves, organises, and manages tasks across pets."""

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    # --- Retrieval --------------------------------------------------------

    def get_todays_tasks(self) -> List[Tuple[str, Task]]:
        """Return all incomplete tasks whose due date is today or earlier."""
        today = date.today()
        return [
            (pn, t)
            for pn, t in self.owner.get_all_tasks()
            if not t.completed and t.due_date <= today
        ]

    # --- Sorting ----------------------------------------------------------

    def sort_by_time(
        self, tasks: Optional[List[Tuple[str, Task]]] = None
    ) -> List[Tuple[str, Task]]:
        """Return tasks sorted chronologically by their 'HH:MM' time field."""
        if tasks is None:
            tasks = self.get_todays_tasks()
        return sorted(tasks, key=lambda x: x[1].time)

    # --- Filtering --------------------------------------------------------

    def filter_by_pet(self, pet_name: str) -> List[Tuple[str, Task]]:
        """Return today's tasks for a specific pet."""
        return [(pn, t) for pn, t in self.get_todays_tasks() if pn == pet_name]

    def filter_by_status(self, completed: bool) -> List[Tuple[str, Task]]:
        """Return all tasks matching the given completion status."""
        return [
            (pn, t)
            for pn, t in self.owner.get_all_tasks()
            if t.completed == completed
        ]

    # --- Conflict detection -----------------------------------------------

    def detect_conflicts(self) -> List[str]:
        """Return warning strings for same-pet tasks scheduled at the same time."""
        warnings: List[str] = []
        for pet in self.owner.pets:
            seen: dict[str, str] = {}
            for task in pet.tasks:
                if task.completed:
                    continue
                if task.time in seen:
                    warnings.append(
                        f"⚠️ Conflict for {pet.name}: "
                        f"'{seen[task.time]}' and '{task.title}' both at {task.time}"
                    )
                else:
                    seen[task.time] = task.title
        return warnings

    # --- Task completion with recurrence ----------------------------------

    def mark_task_complete(self, pet_name: str, task_title: str) -> bool:
        """Mark a task done; automatically enqueue the next recurrence if needed."""
        for pet in self.owner.pets:
            if pet.name != pet_name:
                continue
            for task in pet.tasks:
                if task.title == task_title and not task.completed:
                    next_task = task.mark_complete()
                    if next_task:
                        pet.add_task(next_task)
                    return True
        return False

    # --- Schedule generation ----------------------------------------------

    def generate_schedule(self) -> List[Tuple[str, Task]]:
        """Return today's tasks sorted by priority (high first) then time."""
        return sorted(
            self.get_todays_tasks(),
            key=lambda x: (
                self.PRIORITY_ORDER.get(x[1].priority, 3),
                x[1].time,
            ),
        )
