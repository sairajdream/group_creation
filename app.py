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
student_id TEXT,
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
            status = "Full" if vacancy == 0 else f"{vacancy} spots left"
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
            st.write(f"Group {group[0]} - Members: {', '.join(eval(group[1]))} ({group[2]} vacancies left)")
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
        "Join as Individual",
        "Register Partial Group"
    ])

    if option in ["Form New Group", "Register Partial Group"]:
        prompt = "Enter member details (name and Student ID separated by a comma, one member per line)"
        if option == "Form New Group":
            member_input = st.text_area(prompt, height=150, help="e.g.\nSai Raj Ali, M01044027\nRukky, M01044253\nAmir, M01043484")
            required_members = (2, 4)
            action = "Create Group"
            success_message = "Group created successfully."
        else:
            member_input = st.text_area(prompt, height=150, help="e.g.\nSai Raj Ali, M01044027\nRukky, M01044253")
            required_members = (2, 3)
            action = "Register Partial Group"
            success_message = "Partial Group registered successfully."

        if st.button(action):
            members_list = parse_members(member_input)
            if members_list is None:
                st.error("Please enter valid member details in the correct format.")
                return
            if not required_members[0] <= len(members_list) <= required_members[1]:
                st.error(f"Please enter between {required_members[0]}-{required_members[1]} members.")
            else:
                vacancies = 4 - len(members_list)
                create_group(members_list, vacancies)
                st.success(f"{success_message} {vacancies} spots left!")

    elif option == "Join as Individual":
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
    c.execute("SELECT * FROM groups WHERE vacancies BETWEEN 1 AND 2")
    return c.fetchall()

def get_all_individuals():
    c.execute("SELECT * FROM individuals")
    return c.fetchall()

def check_existing_group(student_id):
    c.execute("SELECT * FROM groups WHERE members LIKE ?", (f"%{student_id}%",))
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
        c.execute("SELECT * FROM individuals WHERE LOWER(name) LIKE ? OR LOWER(student_id) LIKE ?", (f"%{search_term}%", f"%{search_term}%"))
        individual_results = c.fetchall()

        if group_results:
            st.success("Group Found:")
            for group in group_results:
                st.write(f"Group {group[0]} - Members: {', '.join(eval(group[1]))}")
        if individual_results:
            st.warning("Individual Found:")
            for ind in individual_results:
                st.write(f"{ind[1]} ({ind[2]}) - {ind[3]}")

def admin_view():
    st.subheader("Admin Overview")
    st.write("Total Groups:", len(get_all_groups()))
    st.write("Total Individuals Looking for Groups:", len(get_all_individuals()))

if __name__ == "__main__":
    main()
