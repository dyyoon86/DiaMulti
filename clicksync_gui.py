# ---- [1] 자동 의존성 설치 블록 ----
import sys
import subprocess

def pip_install(package):
    try:
        if package == "pywin32":
            import win32api
        elif package == "pyserial":
            import serial
        else:
            __import__(package)
    except ImportError:
        print(f"[INFO] {package} 패키지 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for pkg in ["pygetwindow", "pyautogui", "pywin32", "pyserial"]:
    pip_install(pkg)

# ---- [2] 실제 코드 시작 ----
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pygetwindow as gw
import win32gui
import win32api
import win32con
import pyautogui
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

def get_window_rect(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    return left, top, width, height

def get_relative_ratio(x, y, win_left, win_top, win_w, win_h):
    rel_x = x - win_left
    rel_y = y - win_top
    if rel_x < 0 or rel_y < 0 or rel_x > win_w or rel_y > win_h:
        return None, None, rel_x, rel_y
    ratio_x = rel_x / win_w
    ratio_y = rel_y / win_h
    return ratio_x, ratio_y, rel_x, rel_y

def calc_sub_target(main_rect, sub_rect, click_x, click_y):
    m_left, m_top, m_w, m_h = main_rect
    s_left, s_top, s_w, s_h = sub_rect
    ratio_x, ratio_y, rel_x, rel_y = get_relative_ratio(click_x, click_y, m_left, m_top, m_w, m_h)
    if ratio_x is None:
        return None, None, ratio_x, ratio_y, rel_x, rel_y
    sub_x = int(s_left + ratio_x * s_w)
    sub_y = int(s_top + ratio_y * s_h)
    return sub_x, sub_y, ratio_x, ratio_y, rel_x, rel_y

def get_delta(target_x, target_y):
    cur_x, cur_y = pyautogui.position()
    dx = target_x - cur_x
    dy = target_y - cur_y
    return dx, dy

class ClickSyncGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ClickSync - Tkinter GUI (로그추가)")
        self.running = False
        self.arduino = None

        ttk.Label(root, text="Main Window:").grid(row=0, column=0, padx=5, pady=5)
        self.main_cmb = ttk.Combobox(root, width=40)
        self.main_cmb.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(root, text="Sub Window:").grid(row=1, column=0, padx=5, pady=5)
        self.sub_cmb = ttk.Combobox(root, width=40)
        self.sub_cmb.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(root, text="Refresh Windows", command=self.refresh_windows).grid(row=0, column=2, rowspan=2, padx=5, pady=5)

        ttk.Label(root, text="Arduino Port:").grid(row=2, column=0, padx=5, pady=5)
        self.port_cmb = ttk.Combobox(root, width=25, state="readonly")
        self.port_cmb.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(root, text="Find Ports", command=self.find_ports).grid(row=2, column=2, padx=5, pady=5)

        self.start_btn = tk.Button(root, text="▶ START", bg="lime", fg="black", command=self.start_sync)
        self.start_btn.grid(row=3, column=0, padx=5, pady=10)
        self.stop_btn = tk.Button(root, text="■ STOP", bg="red", fg="white", command=self.stop_sync)
        self.stop_btn.grid(row=3, column=1, padx=5, pady=10)

        self.log_box = tk.Text(root, height=14, width=70)
        self.log_box.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        self.refresh_windows()
        self.find_ports()

    def log(self, msg):
        self.log_box.insert(tk.END, f"{msg}\n")
        self.log_box.see(tk.END)

    def refresh_windows(self):
        titles = [w.title for w in gw.getWindowsWithTitle('') if w.title.strip()]
        self.main_cmb['values'] = titles
        self.sub_cmb['values'] = titles

    def find_ports(self):
        if serial is None:
            self.port_cmb['values'] = []
            self.port_cmb.set("pyserial not installed")
            self.log("pyserial module not found.")
            return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cmb['values'] = ports
        if ports:
            self.port_cmb.set(ports[0])
        else:
            self.port_cmb.set("None")
        self.log(f"Available ports: {ports}")

    def start_sync(self):
        if self.running:
            self.log("Already running.")
            return
        main_title = self.main_cmb.get()
        sub_title = self.sub_cmb.get()
        if not main_title or not sub_title:
            messagebox.showerror("Error", "Please select both main and sub window.")
            return
        self.arduino = None
        port = self.port_cmb.get()
        if port and port not in ("None", "pyserial not installed") and serial is not None:
            try:
                self.arduino = serial.Serial(port, 9600, timeout=1)
                time.sleep(2)
                self.log(f"Connected to Arduino: {port}")
            except Exception as e:
                self.log(f"Serial open error: {e}")
        self.running = True
        self.log("Click sync started. (Click in main window to trigger)")
        threading.Thread(target=self.sync_loop, daemon=True).start()

    def stop_sync(self):
        self.running = False
        if self.arduino:
            self.arduino.close()
            self.arduino = None
        self.log("Click sync stopped.")

    def sync_loop(self):
        main_title = self.main_cmb.get()
        sub_title = self.sub_cmb.get()
        main_win = [w for w in gw.getWindowsWithTitle(main_title) if w.title][0]
        sub_win = [w for w in gw.getWindowsWithTitle(sub_title) if w.title][0]
        main_hwnd = main_win._hWnd
        sub_hwnd = sub_win._hWnd
        main_rect = get_window_rect(main_hwnd)
        sub_rect = get_window_rect(sub_hwnd)
        last_click_time = 0

        # 주요 창 정보 먼저 로그
        self.log(f"[MAIN] {main_title} pos/size: {main_rect}")
        self.log(f"[SUB ] {sub_title} pos/size: {sub_rect}")

        self.log("Waiting for mouse click in main window...")
        while self.running:
            if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
                now = time.time()
                if now - last_click_time > 0.3:
                    x, y = pyautogui.position()
                    sub_x, sub_y, ratio_x, ratio_y, rel_x, rel_y = calc_sub_target(main_rect, sub_rect, x, y)
                    dx, dy = get_delta(sub_x, sub_y) if sub_x is not None else (None, None)

                    # 로그로 상세 출력
                    self.log("="*50)
                    self.log(f"[클릭] 마우스 실제 위치: ({x}, {y})")
                    self.log(f"[MAIN] (left, top, w, h): {main_rect}")
                    self.log(f"[SUB ] (left, top, w, h): {sub_rect}")
                    self.log(f"[MAIN] 클릭 상대좌표: rel_x={rel_x}, rel_y={rel_y}")
                    self.log(f"[MAIN] 클릭 비율: ratio_x={ratio_x}, ratio_y={ratio_y}")
                    if sub_x is not None:
                        self.log(f"[SUB ] 변환 좌표: ({sub_x}, {sub_y})")
                        self.log(f"[DELTA] dx={dx}, dy={dy}")
                        msg = f"{dx},{dy}\n"
                        if self.arduino:
                            try:
                                self.arduino.write(msg.encode())
                                self.log(f"Sent to Arduino: {msg.strip()}")
                            except Exception as e:
                                self.log(f"Write failed: {e}")
                        else:
                            self.log(f"(Test) Would send: {msg.strip()}")
                    else:
                        self.log("[INFO] 클릭 위치가 메인 창 영역을 벗어났음. 무시.")
                    last_click_time = now
            time.sleep(0.01)

if __name__ == "__main__":
    root = tk.Tk()
    app = ClickSyncGUI(root)
    root.mainloop()
