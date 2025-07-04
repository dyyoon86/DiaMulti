import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pygetwindow as gw
import win32gui
import pyautogui
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None  # pyserial이 없어도 실행은 되게 함

class ClickSyncGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ClickSync - PyQt/Tkinter Hybrid")
        self.running = False     # 클릭 감지 루프 동작 여부
        self.arduino = None      # 아두이노 시리얼 객체

        # ---- GUI Layout 구성 ----
        # 메인/서브 창 선택 콤보박스
        ttk.Label(root, text="Main Window:").grid(row=0, column=0, padx=5, pady=5)
        self.main_cmb = ttk.Combobox(root, width=40)
        self.main_cmb.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(root, text="Sub Window:").grid(row=1, column=0, padx=5, pady=5)
        self.sub_cmb = ttk.Combobox(root, width=40)
        self.sub_cmb.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(root, text="Refresh Windows", command=self.refresh_windows).grid(row=0, column=2, rowspan=2, padx=5, pady=5)

        # 아두이노 포트 검색 및 선택
        ttk.Label(root, text="Arduino Port:").grid(row=2, column=0, padx=5, pady=5)
        self.port_cmb = ttk.Combobox(root, width=25, state="readonly")
        self.port_cmb.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(root, text="Find Ports", command=self.find_ports).grid(row=2, column=2, padx=5, pady=5)

        # 시작/중지 버튼
        self.start_btn = tk.Button(root, text="▶ START", bg="lime", fg="black", command=self.start_sync)
        self.start_btn.grid(row=3, column=0, padx=5, pady=10)
        self.stop_btn = tk.Button(root, text="■ STOP", bg="red", fg="white", command=self.stop_sync)
        self.stop_btn.grid(row=3, column=1, padx=5, pady=10)

        # 로그 출력 텍스트박스
        self.log_box = tk.Text(root, height=10, width=65)
        self.log_box.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        # 윈도우 리스트와 포트 리스트 초기화
        self.refresh_windows()
        self.find_ports()

    def log(self, msg):
        """로그를 텍스트박스에 출력"""
        self.log_box.insert(tk.END, f"{msg}\n")
        self.log_box.see(tk.END)

    def refresh_windows(self):
        """PC에 열린 윈도우 창 목록을 콤보박스에 채움"""
        titles = [w.title for w in gw.getWindowsWithTitle('') if w.title.strip()]
        self.main_cmb['values'] = titles
        self.sub_cmb['values'] = titles

    def find_ports(self):
        """연결 가능한 시리얼(아두이노) 포트 검색해서 콤보박스에 채움"""
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
        """감지 루프 시작"""
        if self.running:
            self.log("Already running.")
            return
        main_title = self.main_cmb.get()
        sub_title = self.sub_cmb.get()
        if not main_title or not sub_title:
            messagebox.showerror("Error", "Please select both main and sub window.")
            return
        # 시리얼 포트 연결 (포트 선택, pyserial 설치된 경우만)
        self.arduino = None
        port = self.port_cmb.get()
        if port and port not in ("None", "pyserial not installed") and serial is not None:
            try:
                self.arduino = serial.Serial(port, 9600, timeout=1)
                time.sleep(2)  # 아두이노 리셋 대기
                self.log(f"Connected to Arduino: {port}")
            except Exception as e:
                self.log(f"Serial open error: {e}")
        self.running = True
        self.log("Click sync started. (Click in main window to trigger)")
        threading.Thread(target=self.sync_loop, daemon=True).start()

    def stop_sync(self):
        """감지 루프 중지"""
        self.running = False
        if self.arduino:
            self.arduino.close()
            self.arduino = None
        self.log("Click sync stopped.")

    def sync_loop(self):
        """마우스 클릭을 감지해서 변환/전송"""
        main_title = self.main_cmb.get()
        sub_title = self.sub_cmb.get()
        # 메인/서브 창 정보 얻기
        main_win = [w for w in gw.getWindowsWithTitle(main_title) if w.title][0]
        sub_win = [w for w in gw.getWindowsWithTitle(sub_title) if w.title][0]
        main_hwnd = main_win._hWnd
        sub_hwnd = sub_win._hWnd
        m_left, m_top, m_right, m_bottom = win32gui.GetWindowRect(main_hwnd)
        m_w = m_right - m_left
        m_h = m_bottom - m_top
        s_left, s_top, s_right, s_bottom = win32gui.GetWindowRect(sub_hwnd)
        s_w = s_right - s_left
        s_h = s_bottom - s_top
        last_click_time = 0

        self.log("Waiting for mouse click in main window...")
        while self.running:
            # 마우스 왼쪽버튼 클릭 감지 (0.3초 중복 방지)
            if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
                now = time.time()
                if now - last_click_time > 0.3:
                    x, y = pyautogui.position()   # 현재 마우스 커서 위치
                    rel_x = x - m_left
                    rel_y = y - m_top
                    # 메인 창 영역 안에서 클릭한 것인지 확인
                    if rel_x < 0 or rel_y < 0 or rel_x > m_w or rel_y > m_h:
                        last_click_time = now
                        continue
                    # 비율로 환산해서 서브 창의 타겟 좌표 계산
                    ratio_x = rel_x / m_w
                    ratio_y = rel_y / m_h
                    sub_x = int(s_left + ratio_x * s_w)
                    sub_y = int(s_top + ratio_y * s_h)
                    # 현재 커서와 타겟 간 이동량(Δx, Δy) 계산
                    cur_x, cur_y = pyautogui.position()
                    dx = sub_x - cur_x
                    dy = sub_y - cur_y
                    msg = f"{dx},{dy}\n"
                    # 아두이노 연결되어 있으면 전송, 아니면 콘솔 출력만
                    if self.arduino:
                        try:
                            self.arduino.write(msg.encode())
                            self.log(f"Sent to Arduino: {msg.strip()}")
                        except Exception as e:
                            self.log(f"Write failed: {e}")
                    else:
                        self.log(f"(Test) Would send: {msg.strip()}")
                    last_click_time = now
            time.sleep(0.01)  # 과도한 CPU 점유 방지

if __name__ == "__main__":
    root = tk.Tk()
    app = ClickSyncGUI(root)
    root.mainloop()
