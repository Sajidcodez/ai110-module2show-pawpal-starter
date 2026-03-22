"""
app.py — PawPal+ Streamlit UI.

Connects the Owner / Pet / Task / Scheduler backend to an interactive web UI.
"""

import streamlit as st
from datetime import date

from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session state — persist the Owner across Streamlit reruns
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None  # set once owner name is submitted

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+")
st.caption("A smart pet care planner — daily schedules, conflict warnings, and recurring tasks.")

st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.subheader("1. Owner Info")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    submitted = st.form_submit_button("Save owner")
    if submitted and owner_name.strip():
        st.session_state.owner = Owner(name=owner_name.strip())
        st.success(f"Welcome, {owner_name}!")

if st.session_state.owner is None:
    st.info("Enter your name above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Section 2 — Add a Pet
# ---------------------------------------------------------------------------

st.divider()
st.subheader("2. Add a Pet")

with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "bird", "rabbit", "other"])
    with col3:
        breed = st.text_input("Breed (optional)", value="")

    add_pet = st.form_submit_button("Add pet")
    if add_pet and pet_name.strip():
        existing_names = [p.name for p in owner.pets]
        if pet_name.strip() in existing_names:
            st.warning(f"A pet named '{pet_name}' already exists.")
        else:
            owner.add_pet(Pet(name=pet_name.strip(), species=species, breed=breed.strip()))
            st.success(f"Added {pet_name}!")

if owner.pets:
    st.write("**Your pets:**", ", ".join(p.name for p in owner.pets))

# ---------------------------------------------------------------------------
# Section 3 — Add a Task
# ---------------------------------------------------------------------------

st.divider()
st.subheader("3. Schedule a Task")

if not owner.pets:
    st.info("Add at least one pet first.")
else:
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected_pet = st.selectbox("Pet", [p.name for p in owner.pets])
            task_title = st.text_input("Task title", value="Morning walk")
            task_time = st.text_input("Time (HH:MM)", value="07:00")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=20)
            priority = st.selectbox("Priority", ["high", "medium", "low"])
            frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])

        description = st.text_input("Notes (optional)", value="")
        due = st.date_input("Due date", value=date.today())

        add_task = st.form_submit_button("Add task")
        if add_task and task_title.strip():
            # Validate HH:MM
            try:
                h, m = task_time.strip().split(":")
                assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
                time_str = f"{int(h):02d}:{int(m):02d}"
            except Exception:
                st.error("Please enter a valid time in HH:MM format (e.g. 07:30).")
            else:
                for pet in owner.pets:
                    if pet.name == selected_pet:
                        pet.add_task(Task(
                            title=task_title.strip(),
                            time=time_str,
                            duration_minutes=int(duration),
                            priority=priority,
                            frequency=frequency,
                            description=description.strip(),
                            due_date=due,
                        ))
                        st.success(f"Task '{task_title}' added for {selected_pet}!")
                        break

# ---------------------------------------------------------------------------
# Section 4 — Today's Schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("4. Today's Schedule")

if not owner.pets or not owner.get_all_tasks():
    st.info("Add some tasks to generate a schedule.")
else:
    scheduler = Scheduler(owner)

    # Conflict warnings
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            st.warning(warning)
    else:
        st.success("No scheduling conflicts detected.")

    # Generate schedule
    schedule = scheduler.generate_schedule()

    if not schedule:
        st.info("No tasks due today.")
    else:
        st.write(f"**{len(schedule)} task(s) for today — sorted by priority then time:**")

        rows = []
        for pet_name, task in schedule:
            rows.append({
                "Time": task.time,
                "Task": task.title,
                "Pet": pet_name,
                "Duration": f"{task.duration_minutes} min",
                "Priority": task.priority.capitalize(),
                "Freq": task.frequency,
                "Status": "Done" if task.completed else "Pending",
                "Notes": task.description,
            })
        st.table(rows)

    # --- Mark a task complete -------------------------------------------
    st.write("**Mark a task complete:**")
    with st.form("complete_form"):
        pet_names = [p.name for p in owner.pets]
        complete_pet = st.selectbox("Pet", pet_names, key="complete_pet")
        pet_tasks = [
            t.title
            for p in owner.pets if p.name == complete_pet
            for t in p.tasks if not t.completed
        ]
        if pet_tasks:
            complete_task = st.selectbox("Task", pet_tasks, key="complete_task")
            done_btn = st.form_submit_button("Mark done")
            if done_btn:
                scheduler.mark_task_complete(complete_pet, complete_task)
                st.success(
                    f"'{complete_task}' marked complete!"
                    + (" A new recurrence was added." if any(
                        t.title == complete_task and not t.completed
                        for p in owner.pets if p.name == complete_pet
                        for t in p.tasks
                    ) else "")
                )
                st.rerun()
        else:
            st.info("No pending tasks for this pet.")
            st.form_submit_button("Mark done", disabled=True)

# ---------------------------------------------------------------------------
# Section 5 — All Tasks (filter view)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("5. All Tasks")

if owner.get_all_tasks():
    scheduler = Scheduler(owner)

    col1, col2 = st.columns(2)
    with col1:
        filter_pet = st.selectbox(
            "Filter by pet",
            ["All"] + [p.name for p in owner.pets],
            key="filter_pet",
        )
    with col2:
        filter_status = st.selectbox(
            "Filter by status",
            ["All", "Pending", "Done"],
            key="filter_status",
        )

    all_pairs = owner.get_all_tasks()

    if filter_pet != "All":
        all_pairs = [(pn, t) for pn, t in all_pairs if pn == filter_pet]
    if filter_status == "Pending":
        all_pairs = [(pn, t) for pn, t in all_pairs if not t.completed]
    elif filter_status == "Done":
        all_pairs = [(pn, t) for pn, t in all_pairs if t.completed]

    if all_pairs:
        rows = [
            {
                "Pet": pn,
                "Task": t.title,
                "Time": t.time,
                "Due": str(t.due_date),
                "Priority": t.priority.capitalize(),
                "Freq": t.frequency,
                "Status": "Done" if t.completed else "Pending",
            }
            for pn, t in all_pairs
        ]
        st.table(rows)
    else:
        st.info("No tasks match the current filter.")
else:
    st.info("No tasks added yet.")
