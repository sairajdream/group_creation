import streamlit as st
import sqlite3
import pandas as pd
import os
import requests
from datetime import datetime

# Database file name
DB_FILE = "groups.db"

# GitHub repository details
GITHUB_REPO = "sairajdream/group5"  # Replace with your GitHub username and repository name
GITHUB_FILE_PATH = "groups.db"  # Path to the database file in the repository
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

# Get GitHub token from environment variable

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

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

    st.header("Partial Groups (2-4 Members)")
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

def upload_to_github():
    """Upload the updated database to GitHub."""
    try:
        with open(DB_FILE, "rb") as f:
            content = f.read()

        # Get the SHA of the existing file
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(GITHUB_API_URL, headers=headers)
        sha = response.json().get("sha")

        # Upload the file
        data = {
            "message": "Update database",
            "content": content.encode("base64").decode("utf-8"),
            "sha": sha
        }
        response = requests.put(GITHUB_API_URL, json=data, headers=headers)
        if response.status_code == 200:
            st.success("Database uploaded to GitHub successfully.")
        else:
            st.error("Failed to upload database to GitHub.")
    except Exception as e:
        st.error(f"Error uploading database: {e}")

# Helper functions
def get_all_groups():
    c.execute("SELECT * FROM groups")
    return c.fetchall()

def get_partial_groups():
    c.execute("SELECT * FROM groups WHERE vacancies > 0 AND vacancies < 5")
    return c.fetchall()

def get_all_individuals():
    c.execute("SELECT * FROM individuals")
    return c.fetchall()

if __name__ == "__main__":
    main()
