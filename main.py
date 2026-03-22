"""
main.py — CLI demo / testing ground for PawPal+ backend logic.

Run with:  python main.py
"""

from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler


def print_schedule(schedule):
    """Print a formatted schedule to the terminal."""
    if not schedule:
        print("  (no tasks)")
        return
    for pet_name, task in schedule:
        status = "✅" if task.completed else "🔲"
        print(
            f"  {status} [{task.time}] {task.title} ({pet_name}) "
            f"— {task.duration_minutes} min | {task.priority} priority | {task.frequency}"
        )


def main():
    # --- Setup -----------------------------------------------------------
    owner = Owner(name="Jordan")

    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu")
    whiskers = Pet(name="Whiskers", species="cat", breed="Tabby")

    owner.add_pet(mochi)
    owner.add_pet(whiskers)

    # --- Add tasks (intentionally out of order to test sorting) ----------
    mochi.add_task(Task("Afternoon walk",  "14:00", 30, "medium", "daily"))
    mochi.add_task(Task("Morning walk",    "07:00", 20, "high",   "daily"))
    mochi.add_task(Task("Heartworm pill",  "08:00", 5,  "high",   "weekly",
                        description="Give with food"))
    mochi.add_task(Task("Evening play",    "18:30", 15, "low",    "once"))

    whiskers.add_task(Task("Morning feed",  "07:30", 10, "high",  "daily"))
    whiskers.add_task(Task("Litter clean",  "09:00", 10, "medium","daily"))
    # Intentional conflict — same time as Morning feed
    whiskers.add_task(Task("Brushing",      "07:30", 5,  "low",   "weekly"))

    scheduler = Scheduler(owner)

    # --- Today's schedule (sorted by priority then time) -----------------
    print("\n========== PawPal+ Daily Schedule ==========")
    schedule = scheduler.generate_schedule()
    print_schedule(schedule)

    # --- Conflict detection ----------------------------------------------
    print("\n========== Conflict Warnings ==========")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for w in conflicts:
            print(" ", w)
    else:
        print("  No conflicts detected.")

    # --- Sorting demo ----------------------------------------------------
    print("\n========== Tasks Sorted by Time ==========")
    sorted_tasks = scheduler.sort_by_time()
    print_schedule(sorted_tasks)

    # --- Filtering demo --------------------------------------------------
    print("\n========== Mochi's Tasks Only ==========")
    mochi_tasks = scheduler.filter_by_pet("Mochi")
    print_schedule(mochi_tasks)

    # --- Recurrence demo -------------------------------------------------
    print("\n========== Marking 'Morning walk' complete (daily → recurs) ==========")
    print(f"  Tasks for Mochi before: {len(mochi.tasks)}")
    scheduler.mark_task_complete("Mochi", "Morning walk")
    print(f"  Tasks for Mochi after:  {len(mochi.tasks)}  (new task added for tomorrow)")

    print("\n========== Updated Schedule (after completion) ==========")
    print_schedule(scheduler.generate_schedule())

    print()


if __name__ == "__main__":
    main()
