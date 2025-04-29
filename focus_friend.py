import tkinter as tk
import tkinter.messagebox
import customtkinter as ctk
import os
import sys
import platform
import ctypes
import shutil
import time
import schedule
import threading
from plyer import notification
import re
from datetime import datetime
from collections import deque # For limited-size log

# --- Configuration ---
HOSTS_PATH_WINDOWS = r"C:\Windows\System32\drivers\etc\hosts"
LOCALHOST_IP = "127.0.0.1"
HOSTS_BACKUP_FILENAME = "hosts.focusapp.backup"
TASKS_FILENAME = "focus_tasks.txt"
BLOCKED_SITES_FILENAME = "blocked_sites.txt"
MAX_LOG_ENTRIES = 100
SETTINGS_FILENAME = "focus_app_settings.txt" # To save theme preference

# Default list of websites if the file is empty or doesn't exist
default_websites_to_block = [
    "www.youtube.com", "youtube.com",
    "www.facebook.com", "facebook.com",
    "www.twitter.com", "twitter.com",
    "www.instagram.com", "instagram.com",
    "www.reddit.com", "reddit.com",
    "www.tiktok.com", "tiktok.com",
    "www.netflix.com", "netflix.com",
    "www.twitch.tv", "twitch.tv",
]

# --- Global Variables ---
scheduler_thread = None
stop_scheduler = threading.Event()
current_tasks = []
websites_to_block = []
hosts_backup_path = ""
script_dir = ""
activity_log = deque(maxlen=MAX_LOG_ENTRIES)
app_instance = None

# --- Style Configuration ---
CORNER_RADIUS = 12
BORDER_WIDTH = 2
FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 14
FONT_SIZE_SMALL = 11

# Theme Definitions
THEMES = {
    "light": {
        "background": "#FAEBD7",  # Antique White
        "frame": "#FFF8DC",      # Cornsilk
        "widget_bg": "#FFFFFF",  # White
        "text": "#8B4513",        # Saddle Brown
        "text_light": "#A0522D",  # Sienna
        "accent": "#ADD8E6",      # Light Blue
        "button": "#FFDAB9",      # Peach Puff
        "button_hover": "#FFA07A", # Light Salmon
        "button_secondary": "#E0E0E0", # Light Grey
        "button_secondary_hover": "#C0C0C0", # Silver
        "button_start": "#90EE90", # Light Green
        "button_start_hover": "#3CB371", # Medium Sea Green
        "button_stop": "#F08080", # Light Coral
        "button_stop_hover": "#CD5C5C", # Indian Red
        "disabled": "#D3D3D3",    # Light Gray
        "border": "#8B4513",      # Saddle Brown
        "listbox_select_bg": "#ADD8E6", # Light Blue
        "listbox_select_fg": "#000000", # Black (ensure contrast)
        "status_focus": "#3CB371", # Medium Sea Green (for focusing text)
        "scrollbar_button": "#FFDAB9", # Peach Puff
        "scrollbar_button_hover": "#FFA07A", # Light Salmon
    },
    "dark": {
        "background": "#2B2B2B",  # Dark Grey
        "frame": "#3C3F41",      # Lighter Dark Grey
        "widget_bg": "#45494A",  # Medium Dark Grey
        "text": "#F0E68C",        # Khaki (Light text)
        "text_light": "#D2B48C",  # Tan (Lighter text)
        "accent": "#87CEEB",      # Sky Blue
        "button": "#4682B4",      # Steel Blue
        "button_hover": "#5F9EA0", # Cadet Blue
        "button_secondary": "#696969", # Dim Gray
        "button_secondary_hover": "#808080", # Gray
        "button_start": "#50C878", # Emerald Green
        "button_start_hover": "#3CB371", # Medium Sea Green
        "button_stop": "#CD5C5C", # Indian Red
        "button_stop_hover": "#B22222", # Firebrick
        "disabled": "#555555",    # Dark Gray
        "border": "#F0E68C",      # Khaki (Light border)
        "listbox_select_bg": "#4682B4", # Steel Blue
        "listbox_select_fg": "#FFFFFF", # White
        "status_focus": "#90EE90", # Light Green (stands out on dark)
        "scrollbar_button": "#4682B4", # Steel Blue
        "scrollbar_button_hover": "#5F9EA0", # Cadet Blue
    }
}
active_theme_name = "light" # Default theme

# --- Backend Logic (Mostly unchanged - logging added) ---

def get_script_directory():
    """Gets the directory where the script is running or bundled."""
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    else: return os.path.dirname(os.path.abspath(__file__))

script_dir = get_script_directory()
hosts_backup_path = os.path.join(script_dir, HOSTS_BACKUP_FILENAME)

def add_log_message(message, level="info"):
    """Adds a timestamped message to the activity log and updates the GUI."""
    global activity_log, app_instance
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] {message}"
    activity_log.appendleft(log_entry)
    if app_instance and hasattr(app_instance, 'log_textbox') and app_instance.log_textbox.winfo_exists():
        app_instance.after(0, app_instance.update_log_display)

def is_admin():
    """Checks for Administrator privileges on Windows."""
    try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError: return False

# --- File Operations (Backup, Restore, Load, Save - with logging) ---
# (Functions like backup_hosts_file, restore_hosts_file, block_websites_action, etc.
# remain the same as previous version, ensuring they call add_log_message)
def backup_hosts_file():
    global hosts_backup_path
    if not os.path.exists(hosts_backup_path):
        try:
            add_log_message(f"Backing up hosts file to {HOSTS_BACKUP_FILENAME}...")
            if not os.path.exists(HOSTS_PATH_WINDOWS):
                 add_log_message(f"ERROR: Hosts file not found at {HOSTS_PATH_WINDOWS}", level="error")
                 tkinter.messagebox.showerror("Backup Error", f"Windows hosts file not found at:\n{HOSTS_PATH_WINDOWS}")
                 return False
            shutil.copy(HOSTS_PATH_WINDOWS, hosts_backup_path)
            add_log_message("Backup successful.")
            return True
        except PermissionError:
             add_log_message(f"ERROR: Permission denied creating backup file in {script_dir}.", level="error")
             tkinter.messagebox.showerror("Backup Error", f"Permission denied creating backup file.\nEnsure the application has write permissions in:\n{script_dir}")
             return False
        except Exception as e:
            add_log_message(f"ERROR: Could not back up hosts file: {e}", level="error")
            tkinter.messagebox.showerror("Backup Error", f"Failed to back up hosts file.\n{e}\nCannot proceed.")
            return False
    return True

def restore_hosts_file():
    global hosts_backup_path
    if not hosts_backup_path or not os.path.exists(hosts_backup_path):
        add_log_message("ERROR: Backup file not found. Cannot restore.", level="error")
        tkinter.messagebox.showerror("Restore Error", "Hosts file backup not found. Cannot restore automatically.")
        return False
    try:
        add_log_message("Restoring hosts file from backup...")
        os.makedirs(os.path.dirname(HOSTS_PATH_WINDOWS), exist_ok=True)
        try:
            if os.path.exists(HOSTS_PATH_WINDOWS): os.remove(HOSTS_PATH_WINDOWS)
        except OSError as e: add_log_message(f"Warning: Could not remove current hosts file before restore: {e}", level="warning")
        shutil.copy(hosts_backup_path, HOSTS_PATH_WINDOWS)
        add_log_message("Hosts file restored.")
        flush_dns()
        return True
    except PermissionError as e:
         add_log_message(f"ERROR: Permission denied restoring hosts file: {e}", level="error")
         tkinter.messagebox.showerror("Restore Error", f"Permission denied restoring hosts file.\n{e}\nPlease ensure the app has Admin rights.")
         return False
    except Exception as e:
        add_log_message(f"ERROR: Could not restore hosts file: {e}", level="error")
        tkinter.messagebox.showerror("Restore Error", f"Failed to restore hosts file.\n{e}\nYou may need to restore manually from '{HOSTS_BACKUP_FILENAME}'.")
        return False

def block_websites_action():
    global websites_to_block
    if not is_admin(): add_log_message("Admin privileges required to block websites.", level="error"); return False
    if not backup_hosts_file(): return False
    add_log_message("Applying website blocks...")
    added_count = 0
    try:
        existing_content = ""
        if os.path.exists(HOSTS_PATH_WINDOWS):
            with open(HOSTS_PATH_WINDOWS, 'r', encoding='utf-8', errors='ignore') as file_read: existing_content = file_read.read()
        with open(HOSTS_PATH_WINDOWS, 'a', encoding='utf-8') as file_append:
            if existing_content and not existing_content.endswith(('\n', '\r')): file_append.write('\n')
            for site in websites_to_block:
                entry = f"{LOCALHOST_IP}\t{site}"
                pattern = re.compile(rf"^\s*{re.escape(LOCALHOST_IP)}\s+{re.escape(site)}\s*$", re.MULTILINE)
                if not pattern.search(existing_content):
                     add_log_message(f"Blocking: {site}")
                     file_append.write(f"{entry}\n")
                     added_count += 1
        if added_count > 0: flush_dns()
        add_log_message(f"Website blocking applied. {added_count} new entries added.")
        return True
    except PermissionError:
         add_log_message("ERROR: Permission denied writing to hosts file.", level="error")
         tkinter.messagebox.showerror("Blocking Error", "Permission denied writing to hosts file.\nPlease ensure the app is running as Administrator.")
         return False
    except Exception as e:
        add_log_message(f"ERROR writing to hosts file: {e}", level="error")
        tkinter.messagebox.showerror("Blocking Error", f"Error writing to hosts file:\n{e}")
        return False

def unblock_websites_action():
    if not is_admin(): add_log_message("Admin privileges required to unblock websites.", level="error"); return False
    return restore_hosts_file()

def flush_dns():
    add_log_message("Flushing DNS cache...")
    if platform.system() == "Windows":
        try: os.system("ipconfig /flushdns > nul") ; add_log_message("DNS cache flushed.")
        except Exception as e: add_log_message(f"Warning: Failed to flush DNS cache automatically: {e}", level="warning")
    else: add_log_message("DNS flush command only configured for Windows.", level="info")

def send_task_reminder():
    global current_tasks
    task_to_remind = current_tasks[0] if current_tasks else None
    if task_to_remind: message = f"Focus Reminder: Remember your task - {task_to_remind}"; log_msg = f"Reminder sent for task: {task_to_remind}"
    else: message = "Focus Reminder: Stay on track!"; log_msg = "Generic focus reminder sent."
    add_log_message(log_msg)
    try: notification.notify(title='Focus Session Reminder', message=message, app_name='Focus App', timeout=15)
    except Exception as e: add_log_message(f"Failed to send desktop notification: {e}", level="warning")

def load_list_from_file(filename, default_list):
    file_path = os.path.join(script_dir, filename)
    items = []
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: items = [line.strip() for line in f if line.strip()]
            add_log_message(f"Loaded {len(items)} items from {filename}.")
            return items if items else default_list
        except Exception as e:
            add_log_message(f"Error loading {filename}: {e}", level="error")
            tkinter.messagebox.showwarning("Load Error", f"Could not load {filename}:\n{e}\nUsing default list.")
            return default_list
    else:
        add_log_message(f"{filename} not found, using/saving default list.")
        save_list_to_file(filename, default_list)
        return default_list

def save_list_to_file(filename, item_list):
    file_path = os.path.join(script_dir, filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in item_list: f.write(item + '\n')
    except Exception as e:
        add_log_message(f"Error saving {filename}: {e}", level="error")
        tkinter.messagebox.showerror("Save Error", f"Could not save {filename}:\n{e}")

# --- Settings Load/Save ---
def load_settings():
    """Loads app settings like theme preference."""
    global active_theme_name
    settings_path = os.path.join(script_dir, SETTINGS_FILENAME)
    settings = {"theme": "light"} # Default settings
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        settings[key.strip()] = value.strip()
            add_log_message(f"Settings loaded from {SETTINGS_FILENAME}.")
        except Exception as e:
            add_log_message(f"Error loading settings: {e}. Using defaults.", level="warning")
    active_theme_name = settings.get("theme", "light")
    if active_theme_name not in THEMES: # Validate theme name
        add_log_message(f"Invalid theme '{active_theme_name}' in settings. Using 'light'.", level="warning")
        active_theme_name = "light"

def save_settings():
    """Saves app settings."""
    settings_path = os.path.join(script_dir, SETTINGS_FILENAME)
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(f"theme = {active_theme_name}\n")
        add_log_message(f"Settings saved to {SETTINGS_FILENAME}.")
    except Exception as e:
        add_log_message(f"Error saving settings: {e}", level="error")


def run_scheduler():
    add_log_message("Scheduler thread started.")
    while not stop_scheduler.is_set():
        try: schedule.run_pending()
        except Exception as e: add_log_message(f"Error in scheduler loop: {e}", level="error")
        stop_requested = stop_scheduler.wait(timeout=1.0)
        if stop_requested: break
    add_log_message("Scheduler thread stopped.")

# --- Main Application Class ---
class FocusAppGUI(ctk.CTk):

    def __init__(self):
        super().__init__()
        global app_instance, active_theme_name
        app_instance = self

        # --- Basic Setup & Initial Theme ---
        self.title("🌸 Focus Friend 🌸")
        self.geometry("650x750") # Increased height for theme switch

        load_settings() # Load saved theme preference
        ctk.set_appearance_mode(active_theme_name.capitalize()) # "Light" or "Dark"

        self.current_theme_colors = THEMES[active_theme_name]
        self.configure(fg_color=self.current_theme_colors["background"])

        self.is_running = False
        self.session_end_time = None

        # --- Load Data ---
        global current_tasks, websites_to_block
        add_log_message("Application starting...")
        current_tasks = load_list_from_file(TASKS_FILENAME, [])
        websites_to_block = load_list_from_file(BLOCKED_SITES_FILENAME, default_websites_to_block)

        # --- Check Admin Rights ---
        if platform.system() == "Windows":
            if not is_admin():
                add_log_message("WARNING: Application not run as Administrator. Website blocking will fail.", level="warning")
                tkinter.messagebox.showwarning("Administrator Recommended",
                                            "Run this application as Administrator to enable website blocking features.")
            else:
                 add_log_message("Application running as Administrator.")

        # --- Configure Main Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Tab view expands
        self.grid_rowconfigure(1, weight=0) # Bottom frame does not expand

        # --- Create Tab View with Custom Style ---
        # (Tab view creation moved to _apply_theme to re-create on theme change if needed)
        self._create_tab_view()

        # --- Populate Tabs ---
        # (Tab content creation moved to _apply_theme)
        self._create_all_tabs_content()

        # --- Create Bottom Frame for Theme Switch ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.bottom_frame.grid_columnconfigure(1, weight=1) # Make switch align right

        self.theme_label = self._create_styled_label(self.bottom_frame, text="Mode:", size=FONT_SIZE_SMALL)
        self.theme_label.grid(row=0, column=0, padx=(5, 2), pady=5, sticky="e")

        self.theme_switch_var = ctk.StringVar(value=active_theme_name)
        self.theme_switch = ctk.CTkSwitch(self.bottom_frame,
                                          text="Dark" if active_theme_name == "dark" else "Light",
                                          command=self.toggle_theme,
                                          variable=self.theme_switch_var,
                                          onvalue="dark", offvalue="light",
                                          progress_color=self.current_theme_colors["button_hover"],
                                          fg_color=self.current_theme_colors["button_secondary"],
                                          button_color=self.current_theme_colors["button"],
                                          button_hover_color=self.current_theme_colors["button_hover"],
                                          text_color=self.current_theme_colors["text"],
                                          font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SMALL))
        self.theme_switch.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="e")


        # --- Handle Window Closing ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        add_log_message("Application initialized.")
        # Apply initial theme styles thoroughly after all widgets created
        self._apply_theme_to_widgets()


    def _create_tab_view(self):
         """Creates or re-creates the tab view based on the current theme."""
         if hasattr(self, 'tab_view') and self.tab_view.winfo_exists():
             self.tab_view.destroy() # Remove old one if exists

         self.tab_view = ctk.CTkTabview(self,
                                       anchor="nw",
                                       corner_radius=CORNER_RADIUS,
                                       border_width=BORDER_WIDTH,
                                       border_color=self.current_theme_colors["border"],
                                       fg_color=self.current_theme_colors["frame"],
                                       segmented_button_fg_color=self.current_theme_colors["widget_bg"],
                                       segmented_button_selected_color=self.current_theme_colors["button"],
                                       segmented_button_selected_hover_color=self.current_theme_colors["button_hover"],
                                       segmented_button_unselected_color=self.current_theme_colors["widget_bg"],
                                       segmented_button_unselected_hover_color=self.current_theme_colors["accent"],
                                       text_color=self.current_theme_colors["text"]
                                       )
         self.tab_view.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
         self.tab_view.add("Session")
         self.tab_view.add("Blocked Sites")
         self.tab_view.add("Activity Log")

    def _create_all_tabs_content(self):
         """Calls the creation methods for the content of all tabs."""
         self._create_focus_session_tab()
         self._create_blocked_sites_tab()
         self._create_activity_log_tab()


    def _create_styled_frame(self, parent):
        """Helper to create consistently styled frames."""
        return ctk.CTkFrame(parent,
                            fg_color=self.current_theme_colors["frame"],
                            border_color=self.current_theme_colors["border"],
                            border_width=BORDER_WIDTH,
                            corner_radius=CORNER_RADIUS)

    def _create_styled_button(self, parent, text, command, color_key="button", hover_key="button_hover", text_color_key="text", state=tk.NORMAL, width=120, height=35):
         """Helper to create consistently styled buttons using theme keys."""
         return ctk.CTkButton(parent,
                              text=text,
                              command=command,
                              fg_color=self.current_theme_colors[color_key],
                              hover_color=self.current_theme_colors[hover_key],
                              text_color=self.current_theme_colors[text_color_key] if text_color_key in self.current_theme_colors else text_color_key, # Allow literal colors like #FFFFFF
                              border_color=self.current_theme_colors["border"],
                              border_width=BORDER_WIDTH,
                              corner_radius=CORNER_RADIUS,
                              font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_NORMAL, weight="bold"),
                              state=state,
                              width=width,
                              height=height)

    def _create_styled_label(self, parent, text, size=FONT_SIZE_NORMAL, weight="normal"):
         """Helper to create consistently styled labels."""
         return ctk.CTkLabel(parent,
                             text=text,
                             text_color=self.current_theme_colors["text"],
                             font=ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight))

    def _create_styled_entry(self, parent, placeholder="", width=100):
         """Helper to create consistently styled entry fields."""
         return ctk.CTkEntry(parent,
                             width=width,
                             placeholder_text=placeholder,
                             fg_color=self.current_theme_colors["widget_bg"],
                             text_color=self.current_theme_colors["text"],
                             placeholder_text_color=self.current_theme_colors["text_light"],
                             border_color=self.current_theme_colors["border"],
                             border_width=BORDER_WIDTH,
                             corner_radius=CORNER_RADIUS,
                             font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_NORMAL))


    def _create_focus_session_tab(self):
        """Creates widgets for the Focus Session tab."""
        self.tab_focus = self.tab_view.tab("Session")
        self.tab_focus.configure(fg_color=self.current_theme_colors["background"])
        self.tab_focus.grid_columnconfigure(0, weight=1)
        self.tab_focus.grid_rowconfigure(3, weight=1)

        # Controls Frame
        self.controls_group = ctk.CTkFrame(self.tab_focus, fg_color="transparent")
        self.controls_group.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.controls_group.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._create_styled_label(self.controls_group, text="Duration (min):").grid(row=0, column=0, padx=(5,2), pady=5, sticky="e")
        self.duration_entry = self._create_styled_entry(self.controls_group, placeholder="e.g., 50", width=70)
        self.duration_entry.grid(row=0, column=1, padx=(0, 15), pady=5, sticky="w")
        self.duration_entry.insert(0, "50")

        self._create_styled_label(self.controls_group, text="Reminder (min):").grid(row=0, column=2, padx=(5,2), pady=5, sticky="e")
        self.reminder_entry = self._create_styled_entry(self.controls_group, placeholder="e.g., 25", width=70)
        self.reminder_entry.grid(row=0, column=3, padx=(0, 5), pady=5, sticky="w")
        self.reminder_entry.insert(0, "25")

        # Status and Timer Frame
        self.status_frame = self._create_styled_frame(self.tab_focus)
        self.status_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = self._create_styled_label(self.status_frame, text="Status: Idle", size=FONT_SIZE_LARGE, weight="bold")
        self.status_label.grid(row=0, column=0, padx=10, pady=(5, 0))
        self.timer_label = self._create_styled_label(self.status_frame, text="", size=FONT_SIZE_NORMAL)
        self.timer_label.grid(row=1, column=0, padx=10, pady=(0, 5))

        # Start/Stop Buttons Frame
        self.button_frame = ctk.CTkFrame(self.tab_focus, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_button = self._create_styled_button(self.button_frame, text="Start Focus", command=self.start_action, color_key="button_start", hover_key="button_start_hover", text_color_key="#FFFFFF", width=150)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.stop_button = self._create_styled_button(self.button_frame, text="Stop Focus", command=self.stop_action, color_key="button_stop", hover_key="button_stop_hover", text_color_key="#FFFFFF", state=tk.DISABLED, width=150)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Task Management Frame
        self.task_frame = self._create_styled_frame(self.tab_focus)
        self.task_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        self.task_frame.grid_columnconfigure(0, weight=1)
        self.task_frame.grid_rowconfigure(1, weight=1)

        self._create_styled_label(self.task_frame, text="Focus Tasks", size=FONT_SIZE_LARGE, weight="bold").grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5))

        self.task_listbox = tk.Listbox(self.task_frame, height=8, borderwidth=0, highlightthickness=0, relief=tk.FLAT, selectmode=tk.SINGLE)
        self.task_listbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        # Style applied later by _apply_theme_to_widgets

        self.task_scrollbar = ctk.CTkScrollbar(self.task_frame, command=self.task_listbox.yview) # Style applied later
        self.task_scrollbar.grid(row=1, column=2, padx=(0,10), pady=5, sticky="ns")
        self.task_listbox.configure(yscrollcommand=self.task_scrollbar.set)
        self.refresh_task_listbox()

        # Add/Remove Task Frame
        self.task_actions_frame = ctk.CTkFrame(self.task_frame, fg_color="transparent")
        self.task_actions_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        self.task_actions_frame.grid_columnconfigure(0, weight=1)

        self.task_entry = self._create_styled_entry(self.task_actions_frame, placeholder="Enter new task...")
        self.task_entry.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        self.task_entry.bind("<Return>", self.add_task_action)

        self.add_task_button = self._create_styled_button(self.task_actions_frame, text="Add Task", width=100, command=self.add_task_action)
        self.add_task_button.grid(row=0, column=1, padx=5, pady=5)
        self.remove_task_button = self._create_styled_button(self.task_actions_frame, text="Remove", width=100, command=self.remove_task_action, color_key="button_secondary", hover_key="button_secondary_hover")
        self.remove_task_button.grid(row=0, column=2, padx=5, pady=5)


    def _create_blocked_sites_tab(self):
        """Creates widgets for the Blocked Sites tab."""
        self.tab_sites = self.tab_view.tab("Blocked Sites")
        self.tab_sites.configure(fg_color=self.current_theme_colors["background"])
        self.tab_sites.grid_columnconfigure(0, weight=1)
        self.tab_sites.grid_rowconfigure(0, weight=1)

        # Blocked Sites List Frame
        self.sites_list_frame = self._create_styled_frame(self.tab_sites)
        self.sites_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.sites_list_frame.grid_columnconfigure(0, weight=1)
        self.sites_list_frame.grid_rowconfigure(1, weight=1)

        self._create_styled_label(self.sites_list_frame, text="Blocked Websites", size=FONT_SIZE_LARGE, weight="bold").grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5))

        self.sites_listbox = tk.Listbox(self.sites_list_frame, height=15, borderwidth=0, highlightthickness=0, relief=tk.FLAT, selectmode=tk.EXTENDED)
        self.sites_listbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        # Style applied later by _apply_theme_to_widgets

        self.sites_scrollbar = ctk.CTkScrollbar(self.sites_list_frame, command=self.sites_listbox.yview) # Style applied later
        self.sites_scrollbar.grid(row=1, column=2, padx=(0,10), pady=5, sticky="ns")
        self.sites_listbox.configure(yscrollcommand=self.sites_scrollbar.set)
        self.refresh_sites_listbox()

        # Add/Remove Site Frame
        self.site_actions_frame = ctk.CTkFrame(self.sites_list_frame, fg_color="transparent")
        self.site_actions_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        self.site_actions_frame.grid_columnconfigure(0, weight=1)

        self.site_entry = self._create_styled_entry(self.site_actions_frame, placeholder="Enter website URL (e.g., www.example.com)")
        self.site_entry.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        self.site_entry.bind("<Return>", self.add_site_action)

        self.add_site_button = self._create_styled_button(self.site_actions_frame, text="Add Site", width=100, command=self.add_site_action)
        self.add_site_button.grid(row=0, column=1, padx=5, pady=5)
        self.remove_site_button = self._create_styled_button(self.site_actions_frame, text="Remove Selected", width=160, command=self.remove_site_action, color_key="button_secondary", hover_key="button_secondary_hover")
        self.remove_site_button.grid(row=0, column=2, padx=5, pady=5)


    def _create_activity_log_tab(self):
        """Creates widgets for the Activity Log tab."""
        self.tab_log = self.tab_view.tab("Activity Log")
        self.tab_log.configure(fg_color=self.current_theme_colors["background"])
        self.tab_log.grid_columnconfigure(0, weight=1)
        self.tab_log.grid_rowconfigure(0, weight=1)

        self.log_textbox = ctk.CTkTextbox(self.tab_log,
                                          state=tk.DISABLED,
                                          wrap=tk.WORD,
                                          font=(FONT_FAMILY, FONT_SIZE_SMALL),
                                          corner_radius=CORNER_RADIUS,
                                          border_width=BORDER_WIDTH) # Style applied later
        self.log_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        # Style applied later by _apply_theme_to_widgets
        self.update_log_display() # Initial population


    def _configure_listbox_style(self, listbox_widget):
        """Applies custom theme colors to a standard tk.Listbox."""
        try:
            listbox_widget.configure(
                bg=self.current_theme_colors["widget_bg"],
                fg=self.current_theme_colors["text"],
                selectbackground=self.current_theme_colors["listbox_select_bg"],
                selectforeground=self.current_theme_colors["listbox_select_fg"],
                font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                highlightthickness=BORDER_WIDTH, # Use border width for highlight
                highlightcolor=self.current_theme_colors["border"], # Use border color
                highlightbackground=self.current_theme_colors["widget_bg"], # Match background
                borderwidth=0 # Keep internal border off
            )
        except Exception as e:
            add_log_message(f"Warning: Could not apply full theme to listbox: {e}", level="warning")


    def toggle_theme(self):
        """Switches between light and dark themes."""
        global active_theme_name
        # Determine the new theme
        new_theme_name = self.theme_switch_var.get() # "light" or "dark"
        if new_theme_name == active_theme_name:
            return # No change needed

        add_log_message(f"Switching theme to: {new_theme_name}")
        active_theme_name = new_theme_name
        self.current_theme_colors = THEMES[active_theme_name]

        # Set CTk appearance mode
        ctk.set_appearance_mode(active_theme_name.capitalize()) # "Light" or "Dark"

        # Save the new preference
        save_settings()

        # Update the switch text
        self.theme_switch.configure(text=active_theme_name.capitalize())

        # Apply theme to all relevant widgets
        self._apply_theme_to_widgets()


    def _apply_theme_to_widgets(self):
         """Applies the current theme colors to all necessary widgets."""
         theme = self.current_theme_colors

         # --- Update Root Window & Tabs ---
         self.configure(fg_color=theme["background"])
         if hasattr(self, 'tab_focus'): self.tab_focus.configure(fg_color=theme["background"])
         if hasattr(self, 'tab_sites'): self.tab_sites.configure(fg_color=theme["background"])
         if hasattr(self, 'tab_log'): self.tab_log.configure(fg_color=theme["background"])

         # --- Re-configure CTk Widgets with Explicit Colors ---
         # (Many CTk widgets update with set_appearance_mode, but explicit settings might need refresh)

         # Tab View (Re-create or re-configure if necessary - Re-creating is safer for complex changes)
         # For simplicity, let's try reconfiguring the existing one first
         if hasattr(self, 'tab_view'):
             self.tab_view.configure(border_color=theme["border"],
                                      fg_color=theme["frame"],
                                      segmented_button_fg_color=theme["widget_bg"],
                                      segmented_button_selected_color=theme["button"],
                                      segmented_button_selected_hover_color=theme["button_hover"],
                                      segmented_button_unselected_color=theme["widget_bg"],
                                      segmented_button_unselected_hover_color=theme["accent"],
                                      text_color=theme["text"])

         # Frames (Those created with helper)
         if hasattr(self, 'status_frame'): self.status_frame.configure(fg_color=theme["frame"], border_color=theme["border"])
         if hasattr(self, 'task_frame'): self.task_frame.configure(fg_color=theme["frame"], border_color=theme["border"])
         if hasattr(self, 'sites_list_frame'): self.sites_list_frame.configure(fg_color=theme["frame"], border_color=theme["border"])

         # Labels (Created with helper) - Text color only
         if hasattr(self, 'status_label'): self.status_label.configure(text_color=theme["status_focus"] if self.is_running else theme["text"])
         if hasattr(self, 'timer_label'): self.timer_label.configure(text_color=theme["text"])
         # Other labels inside helpers should update automatically if they only used text_color

         # Entries (Created with helper)
         if hasattr(self, 'duration_entry'): self.duration_entry.configure(fg_color=theme["widget_bg"], text_color=theme["text"], placeholder_text_color=theme["text_light"], border_color=theme["border"])
         if hasattr(self, 'reminder_entry'): self.reminder_entry.configure(fg_color=theme["widget_bg"], text_color=theme["text"], placeholder_text_color=theme["text_light"], border_color=theme["border"])
         if hasattr(self, 'task_entry'): self.task_entry.configure(fg_color=theme["widget_bg"], text_color=theme["text"], placeholder_text_color=theme["text_light"], border_color=theme["border"])
         if hasattr(self, 'site_entry'): self.site_entry.configure(fg_color=theme["widget_bg"], text_color=theme["text"], placeholder_text_color=theme["text_light"], border_color=theme["border"])

         # Buttons (Created with helper)
         if hasattr(self, 'start_button'): self.start_button.configure(fg_color=theme["button_start"], hover_color=theme["button_start_hover"], border_color=theme["border"], text_color="#FFFFFF") # Keep white text
         if hasattr(self, 'stop_button'): self.stop_button.configure(fg_color=theme["button_stop"], hover_color=theme["button_stop_hover"], border_color=theme["border"], text_color="#FFFFFF") # Keep white text
         if hasattr(self, 'add_task_button'): self.add_task_button.configure(fg_color=theme["button"], hover_color=theme["button_hover"], border_color=theme["border"], text_color=theme["text"])
         if hasattr(self, 'remove_task_button'): self.remove_task_button.configure(fg_color=theme["button_secondary"], hover_color=theme["button_secondary_hover"], border_color=theme["border"], text_color=theme["text"])
         if hasattr(self, 'add_site_button'): self.add_site_button.configure(fg_color=theme["button"], hover_color=theme["button_hover"], border_color=theme["border"], text_color=theme["text"])
         if hasattr(self, 'remove_site_button'): self.remove_site_button.configure(fg_color=theme["button_secondary"], hover_color=theme["button_secondary_hover"], border_color=theme["border"], text_color=theme["text"])

         # Scrollbars
         if hasattr(self, 'task_scrollbar'): self.task_scrollbar.configure(button_color=theme["scrollbar_button"], button_hover_color=theme["scrollbar_button_hover"], fg_color=theme["frame"])
         if hasattr(self, 'sites_scrollbar'): self.sites_scrollbar.configure(button_color=theme["scrollbar_button"], button_hover_color=theme["scrollbar_button_hover"], fg_color=theme["frame"])

         # Log Textbox
         if hasattr(self, 'log_textbox'): self.log_textbox.configure(fg_color=theme["widget_bg"], text_color=theme["text"], border_color=theme["border"])

         # Theme Switch itself
         if hasattr(self, 'theme_label'): self.theme_label.configure(text_color=theme["text"])
         if hasattr(self, 'theme_switch'): self.theme_switch.configure(progress_color=theme["button_hover"], fg_color=theme["button_secondary"], button_color=theme["button"], button_hover_color=theme["button_hover"], text_color=theme["text"])

         # --- Manually Re-configure tk Widgets ---
         if hasattr(self, 'task_listbox'): self._configure_listbox_style(self.task_listbox)
         if hasattr(self, 'sites_listbox'): self._configure_listbox_style(self.sites_listbox)

         add_log_message(f"Theme applied: {active_theme_name}")


    # --- UI Actions (Tasks & Sites - Logging included) ---
    # (These functions remain the same logic as v3, just ensure they use add_log_message)
    def add_task_action(self, event=None):
        global current_tasks
        task = self.task_entry.get().strip()
        if task:
            if task not in current_tasks:
                add_log_message(f"Task added: '{task}'")
                current_tasks.append(task)
                self.task_listbox.insert(tk.END, task)
                self.task_entry.delete(0, tk.END)
                save_list_to_file(TASKS_FILENAME, current_tasks)
            else: tkinter.messagebox.showinfo("Duplicate Task", "This task is already in the list.")
        else: tkinter.messagebox.showwarning("Empty Task", "Please enter a task description.")

    def remove_task_action(self):
        global current_tasks
        selected_indices = self.task_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            task_to_remove = self.task_listbox.get(index)
            add_log_message(f"Task removed: '{task_to_remove}'")
            current_tasks.remove(task_to_remove)
            self.task_listbox.delete(index)
            save_list_to_file(TASKS_FILENAME, current_tasks)
        else: tkinter.messagebox.showwarning("No Selection", "Please select a task to remove.")

    def add_site_action(self, event=None):
        global websites_to_block
        site = self.site_entry.get().strip().lower()
        if site and ('.' in site and not site.startswith('.') and not site.endswith('.')):
            site = re.sub(r'^https?://', '', site)
            added_list = []
            # Add the entered site if not present
            if site not in websites_to_block:
                 websites_to_block.append(site)
                 added_list.append(site)
            # Determine the www/non-www counterpart
            www_site = f"www.{site}" if not site.startswith("www.") else site[4:]
            # Add the counterpart only if it's different and not already present
            if www_site != site and www_site not in websites_to_block:
                 websites_to_block.append(www_site)
                 added_list.append(www_site)

            if added_list:
                add_log_message(f"Blocked site(s) added: {', '.join(added_list)}")
                websites_to_block.sort()
                self.refresh_sites_listbox()
                self.site_entry.delete(0, tk.END)
                save_list_to_file(BLOCKED_SITES_FILENAME, websites_to_block)
            else: tkinter.messagebox.showinfo("Duplicate Site", f"'{site}' (and its www/non-www variant) is already in the block list.")
        elif not site: tkinter.messagebox.showwarning("Empty Site", "Please enter a website URL.")
        else: tkinter.messagebox.showwarning("Invalid Format", "Please enter a valid website domain (e.g., www.example.com or example.com).")

    def remove_site_action(self):
        global websites_to_block
        selected_indices = self.sites_listbox.curselection()
        if selected_indices:
            removed_list = []
            indices_to_remove = sorted(selected_indices, reverse=True)
            for index in indices_to_remove:
                site_to_remove = self.sites_listbox.get(index)
                if site_to_remove in websites_to_block:
                    websites_to_block.remove(site_to_remove)
                    self.sites_listbox.delete(index)
                    removed_list.append(site_to_remove)
            if removed_list:
                 add_log_message(f"Blocked site(s) removed: {', '.join(removed_list)}")
                 save_list_to_file(BLOCKED_SITES_FILENAME, websites_to_block)
        else: tkinter.messagebox.showwarning("No Selection", "Please select one or more sites to remove.")

    def refresh_task_listbox(self):
        self.task_listbox.delete(0, tk.END)
        for task in current_tasks: self.task_listbox.insert(tk.END, task)

    def refresh_sites_listbox(self):
        self.sites_listbox.delete(0, tk.END)
        websites_to_block.sort()
        for site in websites_to_block: self.sites_listbox.insert(tk.END, site)

    # --- UI Actions (Focus Session - Logging included) ---
    def start_action(self):
        global scheduler_thread, stop_scheduler, websites_to_block
        if self.is_running: return
        try:
            duration_min = int(self.duration_entry.get()); reminder_min = int(self.reminder_entry.get())
            if duration_min <= 0 or reminder_min <= 0: raise ValueError()
        except ValueError: tkinter.messagebox.showerror("Invalid Input", "Please enter valid positive numbers for duration and reminder."); return
        if platform.system() == "Windows" and not is_admin(): tkinter.messagebox.showerror("Admin Required", "Administrator privileges needed to block websites.\nPlease restart as Administrator."); return
        if not websites_to_block: add_log_message("Start cancelled: Blocked sites list is empty.", level="warning"); tkinter.messagebox.showwarning("No Sites Blocked", "Your blocked sites list is empty. Add sites first."); return
        if not block_websites_action(): add_log_message("Session start failed: Could not apply website blocks.", level="error"); return

        add_log_message(f"Focus session started (Duration: {duration_min} min, Reminder: {reminder_min} min).")
        self.is_running = True; self._update_ui_state()
        schedule.clear(); schedule.every(reminder_min).minutes.do(send_task_reminder); send_task_reminder()
        stop_scheduler.clear(); scheduler_thread = threading.Thread(target=run_scheduler, daemon=True); scheduler_thread.start()
        self.session_end_time = time.time() + duration_min * 60; self.update_timer()

    def stop_action(self, ended_naturally=False):
        global scheduler_thread, stop_scheduler
        if not self.is_running: return
        log_reason = "completed" if ended_naturally else "stopped by user"; add_log_message(f"Focus session {log_reason}.")
        stop_scheduler.set(); schedule.clear()
        if platform.system() == "Windows":
            if is_admin():
                 if not unblock_websites_action(): tkinter.messagebox.showwarning("Unblock Failed", "Could not automatically restore hosts file. Check log/permissions.")
            else: add_log_message("Cannot unblock websites without Admin rights.", level="warning"); tkinter.messagebox.showwarning("Admin Required", "Admin rights needed to unblock websites. Restart as Admin or check hosts file manually.")
        self.is_running = False; self._update_ui_state()
        self.session_end_time = None; self.timer_label.configure(text="")
        if scheduler_thread and scheduler_thread.is_alive():
            add_log_message("Waiting for scheduler thread..."); scheduler_thread.join(timeout=2.0)
            if scheduler_thread.is_alive(): add_log_message("Warning: Scheduler thread did not stop cleanly.", level="warning")
        add_log_message("Focus session ended.")

    def _update_ui_state(self):
        """Updates the enable/disable state of UI elements based on is_running."""
        state = tk.DISABLED if self.is_running else tk.NORMAL
        status_text = "Status: Focusing..." if self.is_running else "Status: Idle"
        status_color = self.current_theme_colors["status_focus"] if self.is_running else self.current_theme_colors["text"]

        # Session Controls
        if hasattr(self, 'status_label'): self.status_label.configure(text=status_text, text_color=status_color)
        if hasattr(self, 'start_button'): self.start_button.configure(state=tk.DISABLED if self.is_running else tk.NORMAL)
        if hasattr(self, 'stop_button'): self.stop_button.configure(state=tk.NORMAL if self.is_running else tk.DISABLED)
        if hasattr(self, 'duration_entry'): self.duration_entry.configure(state=state)
        if hasattr(self, 'reminder_entry'): self.reminder_entry.configure(state=state)

        # Task Controls
        if hasattr(self, 'task_entry'): self.task_entry.configure(state=state)
        if hasattr(self, 'add_task_button'): self.add_task_button.configure(state=state)
        if hasattr(self, 'remove_task_button'): self.remove_task_button.configure(state=state)
        if hasattr(self, 'task_listbox'): self.task_listbox.configure(state=state)

    def update_timer(self):
        if self.is_running and self.session_end_time:
            remaining_seconds = int(self.session_end_time - time.time())
            if remaining_seconds > 0:
                minutes, seconds = divmod(remaining_seconds, 60)
                self.timer_label.configure(text=f"~ {minutes:02d}:{seconds:02d} remaining ~")
                self.after(1000, self.update_timer)
            else:
                self.timer_label.configure(text="Session Complete! ✨")
                self.stop_action(ended_naturally=True)
        elif hasattr(self, 'timer_label'): # Ensure label exists before configuring
             self.timer_label.configure(text="")


    def update_log_display(self):
        if not hasattr(self, 'log_textbox') or not self.log_textbox.winfo_exists(): return
        try:
            self.log_textbox.configure(state=tk.NORMAL)
            self.log_textbox.delete("1.0", tk.END)
            log_content = "\n".join(activity_log)
            self.log_textbox.insert("1.0", log_content)
            self.log_textbox.configure(state=tk.DISABLED)
        except Exception as e:
            print(f"Error updating log display: {e}") # Print error for debugging

    def on_closing(self):
        add_log_message("Close requested by user.")
        if self.is_running:
            if tkinter.messagebox.askyesno("Exit Confirmation", "Focus session running!\nExit now to stop the session and unblock sites?\n", icon='warning'):
                add_log_message("Stopping session due to app closing.")
                self.stop_action()
                add_log_message("Exiting application.")
                self.destroy()
            else: add_log_message("Close cancelled by user."); return
        else:
            if scheduler_thread and scheduler_thread.is_alive(): stop_scheduler.set(); scheduler_thread.join(timeout=1.0)
            add_log_message("Exiting application.")
            self.destroy()

# --- Main Execution ---
if __name__ == "__main__":
    if platform.system() == "Windows":
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e: print(f"Note: Could not set DPI awareness ({e}).")

    app = FocusAppGUI()
    app.mainloop()
