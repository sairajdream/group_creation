import streamlit as st
import sqlite3
import pandas as pd
import os
import requests
from datetime import datetime

# Database file name
DB_FILE = "groups.db"

# GitHub repository details
GITHUB_REPO = "sairajdream/group_creation"  # Replace with your GitHub username and repository name
GITHUB_FILE_PATH = "groups.db"  # Path to the database file in the repository
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

# Get GitHub token from environment variable

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    st.error("GitHub token not found. Please set it as an environment variable or in Streamlit Secrets.")

# Check if the database file exists locally
if not os.path.exists(DB_FILE):
    try:
        # Download the database file from GitHub
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(GITHUB_API_URL, headers=headers)
        if response.status_code == 200:
            content = response.json()["content"]
            with open(DB_FILE, "wb") as f:
                f.write(requests.utils.unquote(content).encode("utf-8"))
            st.info("Database loaded from GitHub.")
        else:
            st.warning("Failed to load database from GitHub. Starting with a new database.")
    except Exception as e:
        st.error(f"Error loading database: {e}")

# Connect to the SQLite database
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
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
    menu = ["Dashboard", "Join/Create Group", "Search Members", "Admin View", "Export Data"]
    choice = st.sidebar.radio("Go to", menu)

    if choice == "Dashboard":
        display_dashboard()
    elif choice == "Join/Create Group":
        handle_group_operations()
    elif choice == "Search Members":
        search_functionality()
    elif choice == "Admin View":
        admin_view()
    elif choice == "Export Data":
        export_data()

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

        creator_present = any(student_id in extract_student_id(member) for member in members_list)
        if not creator_present:
            st.error("Your Student ID must be included in the group members.")
            return

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
        for member in members_list:
            member_id = extract_student_id(member)
            remove_individual(member_id)
        st.success(f"Group created successfully with {len(members_list)} members. {vacancies} spot(s) left!")

def manage_my_group():
    st.subheader("Manage My Group")
    student_id = st.text_input("Enter your Student ID to manage your group:")
    if st.button("View My Group"):
        group = check_existing_group(student_id)
        if group:
            st.write(f"Your group details: {group}")
        else:
            st.warning("You are not part of any group.")

def register_individual_option():
    st.subheader("Register as Individual")
    name = st.text_input("Your Name")
    student_id = st.text_input("Your Student ID")
    email = st.text_input("Your Email")

    if st.button("Register"):
        if not name or not student_id or not email:
            st.error("All fields are required.")
            return

        if check_existing_group(student_id):
            st.warning("You are already part of a group.")
            return

        if check_existing_individual(student_id):
            st.warning("You are already registered as an individual.")
            return

        c.execute("INSERT INTO individuals (name, student_id, email, created_at) VALUES (?, ?, ?, ?)",
                  (name, student_id, email, datetime.now()))
        conn.commit()
        st.success("You have been registered as an individual looking for a group.")

def switch_group_option():
    st.subheader("Switch Group")
    student_id = st.text_input("Enter your Student ID to switch groups:")
    if st.button("Switch Group"):
        if not check_existing_group(student_id):
            st.warning("You are not part of any group.")
            return

        c.execute("DELETE FROM groups WHERE members LIKE ?", (f"%({student_id})%",))
        conn.commit()
        st.success("You have been removed from your group. You can now join or create a new group.")

def search_functionality():
    st.subheader("Search Members or Groups")
    search_query = st.text_input("Enter a name or Student ID to search:")
    if st.button("Search"):
        c.execute("SELECT * FROM groups WHERE members LIKE ?", (f"%{search_query}%",))
        groups = c.fetchall()
        if groups:
            st.write("Groups found:")
            for group in groups:
                st.write(group)
        else:
            st.warning("No groups found with the given query.")

def admin_view():
    st.subheader("Admin View")
    st.write("This section is for admin users to manage the database.")
    if st.button("View All Groups"):
        groups = get_all_groups()
        st.write(groups)
    if st.button("View All Individuals"):
        individuals = get_all_individuals()
        st.write(individuals)

def export_data():
    st.subheader("Export Data to CSV")
    groups = get_all_groups()

    # Prepare data in the required format
    export_data = []
    for group in groups:
        group_id = group[0]
        members = eval(group[1])  # Convert string to list
        for member in members:
            name, student_id = member.split(" (")
            student_id = student_id.strip(")")
            export_data.append({
                "Group-number": group_id,
                "Student-name": name,
                "Student-ID": student_id
            })

    # Create a DataFrame
    export_df = pd.DataFrame(export_data)

    # Provide download link
    st.download_button(
        label="Download Group Data as CSV",
        data=export_df.to_csv(index=False).encode('utf-8'),
        file_name="group_data.csv",
        mime="text/csv"
    )

    # Add a download button for the database
    st.subheader("Download Database")
    with open(DB_FILE, "rb") as f:
        st.download_button(
            label="Download Updated Database",
            data=f,
            file_name="groups.db",
            mime="application/octet-stream"
        )

# Helper functions
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

def create_group(members, vacancies):
    c.execute("INSERT INTO groups (members, vacancies, created_at) VALUES (?, ?, ?)",
              (str(members), vacancies, datetime.now()))
    conn.commit()

def remove_individual(student_id):
    c.execute("DELETE FROM individuals WHERE student_id=?", (student_id,))
    conn.commit()

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
    try:
        return member_str.split('(')[1].strip(')')
    except IndexError:
        return ""

def extract_name(member_str):
    try:
        return member_str.split('(')[0].strip()
    except IndexError:
        return ""

if __name__ == "__main__":
    main()
