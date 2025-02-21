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
                <div style='padding:10px; background-color:{color}; border-radius:5px; margin:5px;'>
                    <b>Group {group[0]}</b><br>
                    {status}<br>
                    Members: {', '.join(members)}
                </div>
            """, unsafe_allow_html=True)

    st.header("Partial Groups (2-3 Members)")
    partial_groups = get_partial_groups()
    for group in partial_groups:
        st.write(f"Group {group[0]} - Members: {', '.join(eval(group[1]))} ({group[2]} vacancies left)")

    st.header("Individuals Looking for Groups")
    individuals = get_all_individuals()
    for individual in individuals:
        st.write(f"{individual[1]} ({individual[2]}) - {individual[3]}")

def handle_group_operations():
    st.subheader("Group Operations")
    name = st.text_input("Your Name")
    student_id = st.text_input("Student ID")
    email = st.text_input("MDX Email")

    existing_group = check_existing_group(student_id)
    if existing_group:
        st.success(f"You're already in Group {existing_group[0]}")
        return

    option = st.radio("Select Option", [
        "Form New Group",
        "Join as Individual",
        "Register Partial Group"
    ])

    if option == "Form New Group":
        members = st.text_area("Enter member names (comma separated, 2-4 members)")
        if st.button("Create Group"):
            members_list = [m.strip() for m in members.split(',') if m.strip()]
            if not 2 <= len(members_list) <= 4:
                st.error("Please enter between 2-4 members")
            else:
                vacancies = 4 - len(members_list)
                create_group(members_list, vacancies)
                st.success(f"Group created with {len(members_list)} members. {vacancies} spots left!")
    
    elif option == "Join as Individual":
        if st.button("Register as Looking for Group"):
            register_individual(name, student_id, email)

    elif option == "Register Partial Group":
        members = st.text_area("Enter member names (comma separated, 2-3 members)")
        if st.button("Register Partial Group"):
            members_list = [m.strip() for m in members.split(',') if m.strip()]
            if not 2 <= len(members_list) <= 3:
                st.error("Please enter between 2-3 members")
            else:
                vacancies = 4 - len(members_list)
                create_group(members_list, vacancies)
                st.success(f"Partial Group created with {len(members_list)} members. {vacancies} spots left!")

def create_group(members, vacancies):
    c.execute("INSERT INTO groups (members, vacancies, created_at) VALUES (?, ?, ?)",
             (str(members), vacancies, datetime.now()))
    conn.commit()

def register_individual(name, student_id, email):
    c.execute("SELECT * FROM individuals WHERE student_id=?", (student_id,))
    if c.fetchone():
        st.error("You're already registered as looking for a group")
        return
    c.execute("INSERT INTO individuals (name, student_id, email, created_at) VALUES (?, ?, ?, ?)",
             (name, student_id, email, datetime.now()))
    conn.commit()
    st.success("You've been registered as looking for a group")

def get_all_groups():
    c.execute("SELECT * FROM groups")
    return c.fetchall()

def get_partial_groups():
    c.execute("SELECT * FROM groups WHERE vacancies > 1")
    return c.fetchall()

def get_all_individuals():
    c.execute("SELECT * FROM individuals")
    return c.fetchall()

def check_existing_group(student_id):
    c.execute("SELECT * FROM groups WHERE members LIKE ?", (f"%{student_id}%",))
    return c.fetchone()

def search_functionality():
    st.subheader("Search for Group/Student")
    search_term = st.text_input("Enter name or student ID").strip().lower()
    if search_term:
        c.execute("SELECT * FROM groups WHERE LOWER(members) LIKE ?", (f"%{search_term}%",))
        group_results = c.fetchall()
        c.execute("SELECT * FROM individuals WHERE LOWER(name) LIKE ? OR student_id=?", (f"%{search_term}%", search_term))
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
