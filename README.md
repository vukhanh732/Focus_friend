# Focus Friend 🌸

A simple Windows desktop application designed to help users focus by blocking distracting websites and managing tasks during timed work sessions.

## Features

* **Website Blocking:** Blocks a customizable list of websites by modifying the system's `hosts` file during focus sessions. Requires Administrator privileges.
* **Task Management:** Simple list to add and remove tasks for the current focus session.
* **Timed Focus Sessions:** Set a duration for focused work.
* **Reminders:** Receive periodic desktop notifications during focus sessions.
* **Activity Log:** View a history of application events (session start/stop, reminders, errors, etc.).
* **Customizable Block List:** Add or remove websites from the block list via the UI.
* **Theme Switching:** Toggle between a light (pastel) and dark theme.
* **Persistent Settings:** Saves the blocked sites list, task list, and theme preference between sessions.

## Technologies Used

* **Python 3:** Core programming language.
* **CustomTkinter:** Library for creating the modern graphical user interface (GUI).
* **Tkinter:** Standard Python GUI library (used for Listbox widgets).
* **Plyer:** Library for cross-platform desktop notifications.
* **Schedule:** Library for scheduling reminder tasks.

## Prerequisites

* Python 3 installed (make sure "Add Python to PATH" is checked during installation).
* Required Python libraries installed:
    ```bash
    pip install customtkinter schedule plyer Pillow
    ```

## How to Run

1.  Save the application code as a Python file (e.g., `focus_friend.py`).
2.  Save the required data files (`focus_tasks.txt`, `blocked_sites.txt`, `focus_app_settings.txt`) in the same directory if you want to pre-populate them (the app will create them if they don't exist).
3.  Open Command Prompt or PowerShell **as Administrator**.
4.  Navigate (`cd`) to the directory where you saved the file.
5.  Run the script:
    ```bash
    python focus_friend.py
    ```

## Important Notes

* **Administrator Privileges:** This application **requires Administrator privileges** to function correctly because it modifies the Windows `hosts` file to block websites. You must run the `.py` script "as administrator".
* **Hosts File Backup:** The application creates a backup of your hosts file (`hosts.focusapp.backup`) in its directory before making changes and attempts to restore it when stopping a session or closing.

## Files Created by the App (in the same directory as the script)

* `hosts.focusapp.backup`: Backup of the original Windows hosts file.
* `focus_tasks.txt`: Stores the user's task list.
* `blocked_sites.txt`: Stores the user's custom list of websites to block.
* `focus_app_settings.txt`: Stores user preferences (like the chosen theme).

