import streamlit as st
import sqlite3
from datetime import datetime

# Initialize database
conn = sqlite3.connect('groups.db', check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS groups
(id INTEGER PRIMARY KEY AUTOINCREMENT,
members TEXT,
vacancies INTEGER,
created_at TIMESTAMP)''')

c.execute('''CREATE TABLE IF NOT EXISTS individuals
(id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
student_id TEXT UNIQUE,
email TEXT,
created_at TIMESTAMP)''')
conn.commit()

def main():
    st.title("Group Management System")
    st.sidebar.header("Navigation")
    menu = ["Dashboard", "Join/Create Group", "Search Members", "Admin View"]
    choice = st.sidebar.radio("Go to", menu)

    if choice == "Dashboard":
        display_dashboard()
    elif choice == "Join/Create Group":
        handle_group_operations()
    elif choice == "Search Members":
        search_functionality()
    elif choice == "Admin View":
        admin_view()

def display_dashboard():
    st.header("Groups Overview")
    groups = get_all_groups()
    cols = st.columns(4)

    for idx, group in enumerate(groups):
        with cols[idx % 4]:
            members = eval(group[1])
            vacancy = group[2]
            status = "Full" if vacancy == 0 else f"{vacancy} spot(s) left"
            color = "red" if vacancy == 0 else "green"

            st.markdown(f"""
            <div style="padding:10px; background-color:{color}; border-radius:5px; margin:5px;">
                <b>Group {group[0]}</b><br>
                {status}<br>
                Members: {', '.join(members)}
            </div>
            """, unsafe_allow_html=True)

    st.header("Partial Groups (2-3 Members)")
    partial_groups = get_partial_groups()
    if partial_groups:
        for group in partial_groups:
            st.write(f"**Group {group[0]}** - Members: {', '.join(eval(group[1]))} ({group[2]} spot(s) left)")
            # Note: Direct joining is disabled; management is handled separately.
    else:
        st.write("No partial groups available.")

    st.header("Individuals Looking for Groups")
    individuals = get_all_individuals()
    if individuals:
        for individual in individuals:
            st.write(f"{individual[1]} ({individual[2]}) - {individual[3]}")
    else:
        st.write("No individuals currently looking for groups.")

def handle_group_operations():
    st.subheader("Group Operations")

    option = st.radio("Select Option", [
        "Form New Group",
        "Manage My Group",
        "Register as Individual",
        "Switch Group"
    ])

    if option == "Form New Group":
        form_new_group()
    elif option == "Manage My Group":
        manage_my_group()
    elif option == "Register as Individual":
        register_individual_option()
    elif option == "Switch Group":
        switch_group_option()

def form_new_group():
    st.subheader("Form New Group")
    student_id = st.text_input("Your Student ID")

    if not student_id:
        st.error("Please enter your Student ID to proceed.")
        return

    if check_existing_group(student_id):
        st.warning("You're already in a group. Use 'Manage My Group' to perform group operations.")
        return

    prompt = "Enter member details (name and Student ID separated by a comma, one member per line)"
    member_input = st.text_area(prompt, height=150, help="e.g.\nSai Raj Ali, M01044027\nRukky, M01044253\nAmir, M01043484")

    if st.button("Create Group"):
        members_list = parse_members(member_input)
        if members_list is None:
            st.error("Please enter valid member details in the correct format.")
            return
        if not 2 <= len(members_list) <= 4:
            st.error("Please enter between 2-4 members.")
            return

        # Ensure the creator is part of the group
        creator_present = any(student_id in extract_student_id(member) for member in members_list)
        if not creator_present:
            st.error("Your Student ID must be included in the group members.")
            return

        # Check if any member is already in a group
        conflicting_members = []
        for member in members_list:
            member_id = extract_student_id(member)
            if check_existing_group(member_id):
                conflicting_members.append(extract_name(member))
            elif check_existing_individual(member_id):
                conflicting_members.append(extract_name(member) + f" ({member_id})")

        if conflicting_members:
            st.error(f"The following members are already in a group or registered as individuals: {', '.join(conflicting_members)}")
            return

        vacancies = 4 - len(members_list)
        create_group(members_list, vacancies)
        # Remove added members from individuals if they were registered
        for member in members_list:
            member_id = extract_student_id(member)
            remove_individual(member_id)
        st.success(f"Group created successfully with {len(members_list)} members. {vacancies} spot(s) left!")

def manage_my_group():
    st.subheader("Manage My Group")
    student_id = st.text_input("Your Student ID")

    if not student_id:
        st.error("Please enter your Student ID to proceed.")
        return

    group = get_user_group(student_id)
    if not group:
        st.warning("You are not part of any group. Use 'Form New Group' to create one or contact an existing group to add you.")
        return

    group_id = group[0]
    members = eval(group[1])
    vacancies = group[2]

    st.write(f"**Current Group:** {group_id}")
    st.write(f"**Members:** {', '.join(members)}")
    st.write(f"**Vacancies:** {vacancies}")

    st.markdown("---")
    st.subheader("Add Members to Your Group")

    if vacancies <= 0:
        st.info("Your group is full. No vacancies available.")
    else:
        individuals = get_all_individuals()
        if not individuals:
            st.info("No individuals are currently available to add.")
        else:
            st.write("**Individuals Available to Add:**")
            for ind in individuals:
                st.write(f"{ind[1]} ({ind[2]}) - {ind[3]}")
            selected_individual = st.selectbox("Select an individual to add", individuals, format_func=lambda x: f"{x[1]} ({x[2]})")
            if st.button("Add Member"):
                if vacancies <= 0:
                    st.error("Your group is already full.")
                else:
                    member_str = f"{selected_individual[1]} ({selected_individual[2]})"
                    add_member_to_group(group_id, member_str)
                    remove_individual(selected_individual[2])
                    st.success(f"Added {selected_individual[1]} to Group {group_id}.")
                    # Update vacancies
                    group = get_user_group(student_id)
                    vacancies = group[2]

    st.markdown("---")
    st.subheader("Remove Members from Your Group")
    if len(members) <= 1:
        st.info("Cannot remove members as the group must have at least one member.")
    else:
        member_to_remove = st.selectbox("Select a member to remove", members)
        if st.button("Remove Member"):
            remove_member_from_group(group_id, extract_student_id(member_to_remove))
            # Add the removed member back to individuals
            name = extract_name(member_to_remove)
            student_id_removed = extract_student_id(member_to_remove)
            register_individual(name, student_id_removed, "N/A")  # Email is set to 'N/A' as it's unknown
            st.success(f"Removed {name} from Group {group_id} and added back to individuals.")

def register_individual_option():
    st.subheader("Register as Individual")
    name = st.text_input("Your Name")
    student_id = st.text_input("Your Student ID")
    email = st.text_input("Your MDX Email")

    if st.button("Register as Looking for Group"):
        if not name or not student_id or not email:
            st.error("Please fill in all fields.")
        else:
            if check_existing_group(student_id):
                st.warning("You're already in a group.")
            elif check_existing_individual(student_id):
                st.warning("You're already registered as looking for a group.")
            else:
                register_individual(name, student_id, email)

def switch_group_option():
    st.subheader("Switch Groups")
    student_id = st.text_input("Your Student ID")

    if not student_id:
        st.error("Please enter your Student ID.")
        return

    current_group = get_user_group(student_id)
    if not current_group:
        st.error("You are not part of any group.")
        return

    current_group_id = current_group[0]
    st.write(f"You are currently in **Group {current_group_id}**.")

    if st.button("Leave Current Group and Register as Individual"):
        remove_member_from_group(current_group_id, student_id)
        name = extract_name_from_student_id(student_id)
        email = extract_email_from_student_id(student_id)
        register_individual(name, student_id, email)
        st.success("You have left your current group and been registered as an individual.")

def parse_members(member_input):
    members = []
    lines = member_input.strip().split('\n')
    for line in lines:
        parts = line.split(',')
        if len(parts) != 2:
            return None
        name = parts[0].strip()
        student_id = parts[1].strip()
        if not name or not student_id:
            return None
        members.append(f"{name} ({student_id})")
    return members

def extract_student_id(member_str):
    # Assumes format "Name (StudentID)"
    try:
        return member_str.split('(')[1].strip(')')
    except IndexError:
        return ""

def extract_name(member_str):
    # Assumes format "Name (StudentID)"
    try:
        return member_str.split('(')[0].strip()
    except IndexError:
        return ""

def extract_name_from_student_id(student_id):
    # Search in individuals
    c.execute("SELECT name FROM individuals WHERE student_id=?", (student_id,))
    result = c.fetchone()
    if result:
        return result[0]

    # Search in groups
    c.execute("SELECT members FROM groups WHERE members LIKE ?", (f"%({student_id})%",))
    groups = c.fetchall()
    for group in groups:
        members = eval(group[0])
        for member in members:
            if student_id in member:
                return extract_name(member)
    return "Unknown"

def extract_email_from_student_id(student_id):
    # Search in individuals
    c.execute("SELECT email FROM individuals WHERE student_id=?", (student_id,))
    result = c.fetchone()
    if result:
        return result[0]
    return "N/A"

def create_group(members, vacancies):
    c.execute("INSERT INTO groups (members, vacancies, created_at) VALUES (?, ?, ?)",
              (str(members), vacancies, datetime.now()))
    conn.commit()

def register_individual(name, student_id, email):
    c.execute("INSERT INTO individuals (name, student_id, email, created_at) VALUES (?, ?, ?, ?)",
              (name, student_id, email, datetime.now()))
    conn.commit()
    st.success("You've been registered as looking for a group.")

def get_all_groups():
    c.execute("SELECT * FROM groups")
    return c.fetchall()

def get_partial_groups():
    c.execute("SELECT * FROM groups WHERE vacancies > 0 AND vacancies < 4")
    return c.fetchall()

def get_all_individuals():
    c.execute("SELECT * FROM individuals")
    return c.fetchall()

def check_existing_group(student_id):
    c.execute("SELECT * FROM groups WHERE members LIKE ?", (f"%({student_id})%",))
    return c.fetchone()

def check_existing_individual(student_id):
    c.execute("SELECT * FROM individuals WHERE student_id=?", (student_id,))
    return c.fetchone()

def search_functionality():
    st.subheader("Search for Group/Student")
    search_term = st.text_input("Enter name or Student ID").strip().lower()
    if search_term:
        c.execute("SELECT * FROM groups WHERE LOWER(members) LIKE ?", (f"%{search_term}%",))
        group_results = c.fetchall()
        c.execute("SELECT * FROM individuals WHERE LOWER(name) LIKE ? OR LOWER(student_id) LIKE ?",
                  (f"%{search_term}%", f"%{search_term}%"))
        individual_results = c.fetchall()

        if group_results:
            st.success("Group Found:")
            for group in group_results:
                st.write(f"**Group {group[0]}** - Members: {', '.join(eval(group[1]))}")
        if individual_results:
            st.warning("Individual Found:")
            for ind in individual_results:
                st.write(f"{ind[1]} ({ind[2]}) - {ind[3]}")

def admin_view():
    st.subheader("Admin Overview")
    st.write("Total Groups:", len(get_all_groups()))
    st.write("Total Individuals Looking for Groups:", len(get_all_individuals()))

def get_user_group(student_id):
    c.execute("SELECT * FROM groups WHERE members LIKE ?", (f"%({student_id})%",))
    return c.fetchone()

def remove_member_from_group(group_id, student_id):
    c.execute("SELECT members, vacancies FROM groups WHERE id=?", (group_id,))
    result = c.fetchone()
    if result:
        members = eval(result[0])
        vacancies = result[1]
        # Remove the member
        members = [m for m in members if student_id not in m]
        vacancies += 1
        c.execute("UPDATE groups SET members=?, vacancies=? WHERE id=?",
                  (str(members), vacancies, group_id))
        conn.commit()

def add_member_to_group(group_id, member_str):
    c.execute("SELECT members, vacancies FROM groups WHERE id=?", (group_id,))
    result = c.fetchone()
    if result and result[1] > 0:
        members = eval(result[0])
        vacancies = result[1]
        members.append(member_str)
        vacancies -= 1
        c.execute("UPDATE groups SET members=?, vacancies=? WHERE id=?",
                  (str(members), vacancies, group_id))
        conn.commit()
        st.info(f"Group {group_id} now has {vacancies} vacancy(ies) left.")
    else:
        st.error("Selected group is already full or does not exist.")

def remove_individual(student_id):
    c.execute("DELETE FROM individuals WHERE student_id=?", (student_id,))
    conn.commit()

if __name__ == "__main__":
    main()
