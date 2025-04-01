import time
from tkinter import messagebox
import tkinter as tktk
import ctypes
import sys
import os
import psutil
import win32gui
import win32con
import win32api

import ttkbootstrap as ttk
from ttkbootstrap.style import ThemeDefinition
# config
import json

from user import USER_THEMES as user_themes



def is_fullscreen() -> bool:
    """
    Checks if the current foreground window is in fullscreen mode.
    
    Returns:
        bool: True if a fullscreen application is detected, False otherwise.
    """
    try:
        # Get the handle of the foreground window
        hwnd = win32gui.GetForegroundWindow()

        # Get window rectangle
        window_rect = win32gui.GetWindowRect(hwnd)
        x, y, x1, y1 = window_rect

        # Get screen dimensions
        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        return (x, y, x1, y1) == (0, 0, screen_width, screen_height)
    except Exception as e:
        print("Error while checking fullscreen mode.")
        print(f"Exception: {e}")
        return False

# check if we are running in python.exe (dev mode) or pythonw.exe (production mode)
# if we are running in pythonw.exe, turn stdout and stderr into a file

SCRIPT_LOC = __file__
SCRIPT_DIR = os.path.dirname(SCRIPT_LOC)

if "pythonw.exe" in sys.executable:
    # sys.stdout = open(script_loc + ".out.log", "w")
    # sys.stderr = open(script_loc + ".err.log", "w")
    with open(SCRIPT_LOC + ".out.log", "w") as out_log, \
        open(SCRIPT_LOC + ".err.log", "w") as err_log:
        sys.stdout = out_log
        sys.stderr = err_log
        print("Running in production mode (pythonw.exe)")

WIN_APPID = 'banana.stopwatch.1.0.0'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WIN_APPID)

CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        print("Loading config from file")
        config = json.load(f)
        SW_WIDTH = config["SW_WIDTH"]
        SW_HEIGHT = config["SW_HEIGHT"]
        SW_RIGHTOFF = config["SW_RIGHTOFF"]
        SW_BOTTOMOFF = config["SW_BOTTOMOFF"]
else:
    SW_WIDTH = 180
    SW_HEIGHT = 45
    SW_RIGHTOFF = 400
    SW_BOTTOMOFF = 47
    print("Config file not found, using default values")
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "SW_WIDTH": SW_WIDTH,
            "SW_HEIGHT": SW_HEIGHT,
            "SW_RIGHTOFF": SW_RIGHTOFF,
            "SW_BOTTOMOFF": SW_BOTTOMOFF
        }, f, indent=4)

class Stopwatch:
    def __init__(self):
        theme = user_themes['mocha2']
        self.root = ttk.Window()
        self.root.style.register_theme(ThemeDefinition(
            name='mocha2',
            themetype=theme["type"],
            colors=theme["colors"]
        ))
        self.root.style.theme_use('mocha2')
        # width and height of the monitor
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()

        # self.root.geometry(f"180x45+{width - 400}+{height - 47}")
        self.root.geometry(f"{SW_WIDTH}x{SW_HEIGHT}+{width - SW_RIGHTOFF}+{height - SW_BOTTOMOFF}")
        self.root.title("Stopwatch")
        self.root.overrideredirect(True)
        self.root.resizable(width=False, height=False)
        self.root.attributes("-alpha", 0.89)
        self.root.attributes("-transparentcolor", theme['colors']['bg'])

        self.label = ttk.Label(self.root, text="00:00:00.00", font=("Helvetica", 14))
        self.label.pack()

        self.update_delay = 0

        self.exiting = False

        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)

        self.create_widgets()


        if not os.path.exists(SCRIPT_LOC + ".start_time") and \
            not os.path.exists(SCRIPT_LOC + ".pause_time"):
            self.start_time = None
            self.paused_time = None
            self.paused = False
            self.end_time = None
            self.update_time()
        elif os.path.exists(SCRIPT_LOC + ".start_time"):
            with open(SCRIPT_LOC + ".start_time", "r") as f:
                self.start_time = float(f.read().strip())
            self.start_time = min(self.start_time, time.time())
            self.paused_time = None
            self.paused = False
            self.update_time()
        else:
            self.paused_time = time.time()
            with open(SCRIPT_LOC + ".pause_time", "r") as f:
                self.start_time = self.paused_time - float(f.read().strip())
            self.paused = True

            if self.start_time > time.time():
                self.start_time = time.time()
                self.paused_time = None
                self.paused = False
            else:
                self.pause_button.config(text="Resume")

        self.enforce_topmost()
        self.update_time()
        self.perform()

        self.x = 0
        self.y = 0

    def create_widgets(self):
        self.start_button = ttk.Button(self.root, text="Start", command=self.start, padding=1)
        self.start_button.pack(side="left", padx=2)

        self.pause_button = ttk.Button(self.root, text="Pause", command=self.pause, padding=1)
        self.pause_button.pack(side="left", padx=2)

        self.reset_button = ttk.Button(self.root, text="Reset", command=self.reset, padding=1)
        self.reset_button.pack(side="left", padx=2)

        self.performance_button = ttk.Button(self.root, text=" P ", command=self.perform, padding=1)
        self.performance_button.pack(side="left", padx=2)

        self.drag_button = ttk.Button(self.root, text="   ", padding=1)
        self.drag_button.pack(side="left", padx=2)
        self.drag_button.config(state="disabled")

        self.exit_button = ttk.Button(self.root, text="X", command=self.exit, padding=1)
        self.exit_button.pack(side="right")

    def perform(self):
        if self.update_delay == 0:
            self.update_delay = 0.1
            self.performance_button.config(text=" N ")
        else:
            self.update_delay = 0
            self.performance_button.config(text=" P ")

    def enforce_topmost(self):
        """Ensure the window remains on top even after taskbar interaction."""
        self.root.attributes("-topmost", False)  # Reset topmost
        if not is_fullscreen():
            self.root.attributes("-topmost", True)
        else:
            # make sure we go to bottom
            self.root.lower()  # Move to bottom if fullscreen is detected
        self.root.after(1000, self.enforce_topmost)  # Repeat every second

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self.x
        y = self.root.winfo_y() + event.y - self.y
        self.root.geometry(f"+{x}+{y}")

    def update_time(self):
        if self.start_time is not None:
            if self.paused:
                elapsed_time = self.paused_time - self.start_time
            else:
                elapsed_time = time.time() - self.start_time
            hrs, remainder = divmod(elapsed_time, 3600)
            mins, secs = divmod(remainder, 60)
            self.label.config(text=
                f"{int(hrs):0>2}:{int(mins):0>2}:{int(secs):0>2}.{int(secs * 100 % 100):0>2}")
        # self.root.after(100, self.update_time)

    def exit(self):
        self.exiting = True

    def start(self):
        self.pause_button.config(text="Pause")
        self.start_time = time.time()
        self.paused = False
        with open(SCRIPT_LOC + ".start_time", "w") as f:
            f.write(str(self.start_time))
        if os.path.exists(SCRIPT_LOC + ".pause_time"):
            os.remove(SCRIPT_LOC + ".pause_time")
        

    def pause(self):
        if self.start_time is None:
            messagebox.showinfo("Error", "Stopwatch has not been started")
            return
        if self.paused:
            self.paused = False
            self.start_time = time.time() - (self.paused_time - self.start_time)
            self.paused_time = None
            self.pause_button.config(text="Pause")
            with open(SCRIPT_LOC + ".start_time", "w") as f:
                f.write(str(self.start_time))
            if os.path.exists(SCRIPT_LOC + ".pause_time"):
                os.remove(SCRIPT_LOC + ".pause_time")
        else:
            self.paused = True
            self.paused_time = time.time()
            self.pause_button.config(text="Resume")
            with open(SCRIPT_LOC + ".pause_time", "w") as f:
                f.write(str(self.paused_time - self.start_time))
            if os.path.exists(SCRIPT_LOC + ".start_time"):
                os.remove(SCRIPT_LOC + ".start_time")
            


    def reset(self):
        self.start_time = None
        self.paused_time = None
        self.paused = False
        self.label.config(text="00:00:00.00")
        self.pause_button.config(text="Pause")
        if os.path.exists(SCRIPT_LOC + ".start_time"):
            os.remove(SCRIPT_LOC + ".start_time")
        if os.path.exists(SCRIPT_LOC + ".pause_time"):
            os.remove(SCRIPT_LOC + ".pause_time")
        self.update_time()

    def run(self):
        # we can't just do mainloop since that prevents the time from updating without user input
        while True:
            if self.exiting:
                break
            try:
                self.update_time()
                self.root.update()
                time.sleep(self.update_delay)
            except tktk.TclError:
                print("Window closed, exiting loop.")
                break
        print("Exiting")
        if self.paused:
            self.end_time = self.paused_time
        else:
            self.end_time = time.time()
        if self.start_time is None:
            self.end_time = 0
            self.start_time = 0
        # if os.path.exists(script_loc + ".start_time"):
        #     os.remove(script_loc + ".start_time")
        # if os.path.exists(script_loc + ".pause_time"):
        #     os.remove(script_loc + ".pause_time")
        # maybe, it should always keep its state, and only reset when we click the reset button?
        self.root.destroy()
    
    def elapsed_time(self):
        return self.end_time - self.start_time


def main():
    stopwatch = Stopwatch()

    stopwatch.run()

    elapsed_time = stopwatch.elapsed_time()

    print(f"Elapsed time: {elapsed_time:.2f} seconds")


def main_wrapper():
    # before running main, check if this app is already running to prevent multiple instances
    # if it is, just exit
    for proc in psutil.process_iter():
        try:
            if proc.name() == "pythonw.exe" or proc.name() == "python.exe":
                scrnm = proc.cmdline()[-1]
                cwd = proc.cwd()
                if cwd is None:
                    cwd = ""
                if not os.path.isabs(scrnm):
                    scrnm = os.path.join(cwd, scrnm)
                if os.path.abspath(__file__) == os.path.abspath(scrnm):
                    if proc.pid != os.getpid():
                        print("Stopwatch is already running")
                        sys.exit()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    main()

if __name__ == "__main__":
    main_wrapper()