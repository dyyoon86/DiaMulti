import tkinter as tk
from tkinter import ttk, messagebox
import win32gui
import win32api
import win32con
import pygetwindow as gw
import threading
import time

class ClickSyncGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Click Sync v3.1 GUI")
        self.main_window = None
        self.sub_windows = []
        self.running = False
        self.sync_thread = None
        self.show_click_dot = tk.BooleanVar(value=False)

        self.build_gui()
        self.refresh_window_lists()

    def build_gui(self):
        # Main Window Selector
        ttk.Label(self.root, text="Main Window").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.main_combobox = ttk.Combobox(self.root, width=50)
        self.main_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Sub Window Selector
        ttk.Label(self.root, text="Sub Window").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.sub_combobox = ttk.Combobox(self.root, width=50)
        self.sub_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(self.root, text="Add Sub", command=self.add_sub_window).grid(row=1, column=2, padx=5, pady=5)

        # Sub Window List
        self.sub_listbox = tk.Listbox(self.root, width=75, height=5)
        self.sub_listbox.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        ttk.Button(self.root, text="Remove Selected", command=self.remove_selected_sub).grid(row=2, column=2, padx=5, pady=5)

        # Selected Info Display
        self.selected_info = tk.Text(self.root, height=5, width=80)
        self.selected_info.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

        # Click Dot Toggle
        self.dot_checkbox = ttk.Checkbutton(self.root, text="Show Red Dot on Sub Click", variable=self.show_click_dot)
        self.dot_checkbox.grid(row=4, column=0, padx=5, pady=5, sticky="w")

        # Start and Stop Buttons
        self.start_btn = tk.Button(self.root, text="▶ START SYNC", bg="lime", fg="black", command=self.start_sync)
        self.start_btn.grid(row=5, column=0, padx=5, pady=10)

        self.stop_btn = tk.Button(self.root, text="■ STOP SYNC", bg="red", fg="white", command=self.stop_sync)
        self.stop_btn.grid(row=5, column=1, padx=5, pady=10)

    def refresh_window_lists(self):
        windows = [w.title for w in gw.getWindowsWithTitle('') if w.title.strip()]
        self.main_combobox['values'] = windows
        self.sub_combobox['values'] = windows

    def add_sub_window(self):
        title = self.sub_combobox.get()
        if title and title not in self.sub_windows:
            self.sub_windows.append(title)
            self.sub_listbox.insert(tk.END, title)
            self.update_selected_info()

    def remove_selected_sub(self):
        selected = self.sub_listbox.curselection()
        if selected:
            title = self.sub_listbox.get(selected)
            self.sub_windows.remove(title)
            self.sub_listbox.delete(selected)
            self.update_selected_info()

    def update_selected_info(self):
        info = f"Main Window: {self.main_combobox.get()}\n"
        info += "Sub Windows:\n"
        for title in self.sub_windows:
            info += f" - {title}\n"
        self.selected_info.delete("1.0", tk.END)
        self.selected_info.insert(tk.END, info)

    def start_sync(self):
        if self.running:
            messagebox.showinfo("Info", "Sync already running.")
            return

        main_title = self.main_combobox.get()
        if not main_title:
            messagebox.showerror("Error", "Please select a main window.")
            return

        if not self.sub_windows:
            messagebox.showerror("Error", "Please add at least one sub window.")
            return

        self.running = True
        self.sync_thread = threading.Thread(target=self.sync_loop, daemon=True)
        self.sync_thread.start()

    def stop_sync(self):
        self.running = False
        messagebox.showinfo("Stopped", "Click Sync stopped.")

    def sync_loop(self):
        print("[SYNC] Started click sync loop.")
        main_win = find_window(self.main_combobox.get())
        sub_wins = [find_window(title) for title in self.sub_windows]

        if not main_win or any(w is None for w in sub_wins):
            print("[SYNC] Failed to find all windows.")
            self.running = False
            return

        main_hwnd = main_win._hWnd
        main_left, main_top, main_right, main_bottom = win32gui.GetWindowRect(main_hwnd)
        main_width = main_right - main_left
        main_height = main_bottom - main_top

        while self.running:
            if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
                x, y = win32api.GetCursorPos()
                rel_x = x - main_left
                rel_y = y - main_top

                if rel_x < 0 or rel_y < 0 or rel_x > main_width or rel_y > main_height:
                    time.sleep(0.01)
                    continue

                ratio_x = rel_x / main_width
                ratio_y = rel_y / main_height

                for win in sub_wins:
                    hwnd = win._hWnd
                    sub_left, sub_top, sub_right, sub_bottom = win32gui.GetWindowRect(hwnd)
                    sub_width = sub_right - sub_left
                    sub_height = sub_bottom - sub_top

                    target_x = sub_left + int(ratio_x * sub_width)
                    target_y = sub_top + int(ratio_y * sub_height)

                    client_x, client_y = win32gui.ScreenToClient(hwnd, (target_x, target_y))
                    lParam = win32api.MAKELONG(client_x, client_y)

                    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                    time.sleep(0.05)
                    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

                    if self.show_click_dot.get():
                        print(f"[DOT] Would show red dot at ({target_x}, {target_y})")

                time.sleep(0.3)
            time.sleep(0.01)

def find_window(title):
    for w in gw.getWindowsWithTitle(''):
        if w.title == title:
            return w
    return None

if __name__ == "__main__":
    root = tk.Tk()
    app = ClickSyncGUI(root)
    root.mainloop()
