import time
import ttkbootstrap as ttk
from ttkbootstrap.themes.standard import STANDARD_THEMES
from tkinter import messagebox
import ctypes
import sys
import os
import psutil
import win32gui
import win32con

def is_fullscreen():
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

       # Check if the window dimensions match the screen dimensions (or are very close, allowing for taskbars etc.)
        if (x, y, x1, y1) == (0, 0, screen_width, screen_height):
            return True
        else:
            return False
    except Exception:
        return False

# check if we are running in python.exe (dev mode) or pythonw.exe (production mode)
# if we are running in pythonw.exe, turn stdout and stderr into a file

script_loc = __file__

if "pythonw.exe" in sys.executable:
    sys.stdout = open(script_loc + ".out.log", "w")
    sys.stderr = open(script_loc + ".err.log", "w")

myappid = 'banana.stopwatch.1.0.0'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class Stopwatch:
    def __init__(self):
        THEME_SETTING = 'mocha'
        self.root = ttk.Window(themename=THEME_SETTING)
        # width and height of the monitor
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self.root.geometry("180x45+{}+{}".format(width - 400, height - 47))
        self.root.title("Stopwatch")
        self.root.overrideredirect(True)
        self.root.resizable(width=False, height=False)
        self.root.attributes("-alpha", 0.8)
        self.root.attributes("-transparentcolor", STANDARD_THEMES[THEME_SETTING]['colors']['bg'])

        self.label = ttk.Label(self.root, text="00:00:00.00", font=("Helvetica", 14))
        self.label.pack()

        self.start_time = None
        self.paused_time = None
        self.paused = False
        self.end_time = None
        self.update_time()

        self.update_delay = 0

        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)

        self.start_button = ttk.Button(self.root, text="Start", command=self.start, padding=1)
        self.start_button.pack(side="left", padx=2)

        self.pause_button = ttk.Button(self.root, text="Pause", command=self.pause, padding=1)
        self.pause_button.pack(side="left", padx=2)

        self.reset_button = ttk.Button(self.root, text="Reset", command=self.reset, padding=1)
        self.reset_button.pack(side="left", padx=2)

        self.performance_button = ttk.Button(self.root, text=" P ", command=self.performance, padding=1)
        self.performance_button.pack(side="left", padx=2)

        self.drag_button = ttk.Button(self.root, text="   ", padding=1)
        self.drag_button.pack(side="left", padx=2)
        self.drag_button.config(state="disabled")

        self.exiting = False

        self.exit_button = ttk.Button(self.root, text="X", command=self.exit, padding=1)
        self.exit_button.pack(side="right")

        self.enforce_topmost()
        self.update_time()

    def performance(self):
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
        self.root.after(1000, self.enforce_topmost)  # Repeat every second

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self.x
        y = self.root.winfo_y() + event.y - self.y
        self.root.geometry("+%s+%s" % (x, y))

    def update_time(self):
        if self.start_time is not None:
            if self.paused:
                elapsed_time = self.paused_time - self.start_time
            else:
                elapsed_time = time.time() - self.start_time
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.label.config(text="{:0>2}:{:0>2}:{:0>2}.{:0>2}".format(int(hours), int(minutes), int(seconds), int(seconds * 100 % 100)))
        # self.root.after(100, self.update_time)

    def exit(self):
        self.exiting = True

    def start(self):
        self.pause_button.config(text="Pause")
        self.start_time = time.time()
        self.paused = False

    def pause(self):
        if self.start_time is None:
            messagebox.showinfo("Error", "Stopwatch has not been started")
            return
        if self.paused:
            self.paused = False
            self.start_time = time.time() - (self.paused_time - self.start_time)
            self.paused_time = None
            self.pause_button.config(text="Pause")
        else:
            self.paused = True
            self.paused_time = time.time()
            self.pause_button.config(text="Resume")

    def reset(self):
        self.start_time = None
        self.paused_time = None
        self.paused = False
        self.label.config(text="00:00:00.00")
        self.pause_button.config(text="Pause")

    def run(self):
        # we can't just do mainloop since that prevents the time from updating without user input
        while True:
            if self.exiting:
                break
            try:
                self.update_time()
                self.root.update()
                time.sleep(self.update_delay)
            except:
                break
        print("Exiting")
        if self.paused:
            self.end_time = self.paused_time
        else:
            self.end_time = time.time()
        if self.start_time is None:
            self.end_time = 0
            self.start_time = 0
        self.root.destroy()
    
    def elapsed_time(self):
        return self.end_time - self.start_time


def main():
    stopwatch = Stopwatch()

    stopwatch.run()

    elapsed_time = stopwatch.elapsed_time()

    print("Elapsed time: {:.2f} seconds".format(elapsed_time))
    


if __name__ == "__main__":
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
                        exit()


        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    main()