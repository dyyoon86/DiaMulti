import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Frame
import pygetwindow as gw
import pyautogui
import cv2
import numpy as np
import os
import json
import time
from pynput import mouse

IMG_DIR = "img"

def get_window_list():
    return [w for w in gw.getAllTitles() if w.strip()]

def get_window_rect(title):
    win = gw.getWindowsWithTitle(title)[0]
    return win.left, win.top, win.width, win.height

def template_match_in_window(img_path, left, top, w, h, threshold=0.85):
    scr = pyautogui.screenshot(region=(left, top, w, h))
    scr_np = np.array(scr)
    img_gray = cv2.cvtColor(scr_np, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(img_path, 0)
    if template is None:
        return None
    th, tw = template.shape
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        found_x = left + max_loc[0] + tw // 2
        found_y = top + max_loc[1] + th // 2
        return (found_x, found_y, max_val)
    return None

class ScenarioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("시나리오 빌더 & 자동 실행기 (wait+매크로+멀티삭제)")
        self.geometry("1150x640")
        self.resizable(False, False)
        self.win_titles = get_window_list()
        self.var_sel = tk.StringVar(value=self.win_titles[0] if self.win_titles else "")

        # 최상단: 창 선택
        topbar = Frame(self)
        topbar.pack(fill="x", padx=8, pady=5)
        ttk.Label(topbar, text="대상 창 선택:", font=("맑은 고딕", 11)).pack(side="left")
        self.combo = ttk.Combobox(topbar, textvariable=self.var_sel, values=self.win_titles, width=45)
        self.combo.pack(side="left", padx=5)

        # 전체 그리드: 좌(이미지) - 중간(입력/추가) - 우(시나리오)
        mainframe = Frame(self)
        mainframe.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. 좌측: 이미지 리스트
        left = Frame(mainframe)
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="이미지 목록 (img/)", font=("맑은 고딕", 11, "bold")).pack(anchor="w", pady=3)
        self.img_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(".png")] if os.path.exists(IMG_DIR) else []
        self.list_img = tk.Listbox(left, height=27, width=30)
        for f in self.img_files:
            self.list_img.insert(tk.END, f)
        self.list_img.pack(pady=4, padx=2, fill="y")

        # 2. 중앙: 입력/추가 영역 (카드 스타일)
        center = Frame(mainframe)
        center.grid(row=0, column=1, padx=14, sticky="ns")

        # 이미지 감지 카드
        imgcard = Frame(center, bd=2, relief="groove", bg="#f8f8ff")
        imgcard.pack(pady=7, fill="x")
        ttk.Label(imgcard, text="이미지 감지 단계 추가", background="#f8f8ff",
                  font=("맑은 고딕", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        fimg = Frame(imgcard, bg="#f8f8ff")
        fimg.pack(padx=7, pady=2, fill="x")
        ttk.Label(fimg, text="액션:", background="#f8f8ff").grid(row=0, column=0, padx=2)
        self.var_action_img = tk.StringVar(value="move")
        self.combo_action_img = ttk.Combobox(fimg, textvariable=self.var_action_img,
                                             values=["move", "click", "right_click", "move+click", "move+right_click"], width=15)
        self.combo_action_img.grid(row=0, column=1, padx=2)
        ttk.Label(fimg, text="딜레이(초):", background="#f8f8ff").grid(row=0, column=2, padx=2)
        self.var_delay_img = tk.DoubleVar(value=0.5)
        tk.Entry(fimg, textvariable=self.var_delay_img, width=8).grid(row=0, column=3, padx=2)
        tk.Button(imgcard, text="이미지 단계 추가", command=self.add_step_img, height=2, bg="#e6ecff").pack(pady=4)

        # 좌표 카드
        poscard = Frame(center, bd=2, relief="groove", bg="#f8fff8")
        poscard.pack(pady=7, fill="x")
        ttk.Label(poscard, text="좌표 단계 추가", background="#f8fff8",
                  font=("맑은 고딕", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        fpos = Frame(poscard, bg="#f8fff8")
        fpos.pack(padx=7, pady=2, fill="x")
        ttk.Label(fpos, text="X:", background="#f8fff8").grid(row=0, column=0)
        self.var_x = tk.IntVar(value=0)
        tk.Entry(fpos, textvariable=self.var_x, width=8).grid(row=0, column=1, padx=2)
        ttk.Label(fpos, text="Y:", background="#f8fff8").grid(row=0, column=2)
        self.var_y = tk.IntVar(value=0)
        tk.Entry(fpos, textvariable=self.var_y, width=8).grid(row=0, column=3, padx=2)
        ttk.Label(fpos, text="액션:", background="#f8fff8").grid(row=1, column=0)
        self.var_action_pos = tk.StringVar(value="move")
        self.combo_action_pos = ttk.Combobox(fpos, textvariable=self.var_action_pos,
                                             values=["move", "click", "right_click", "move+click", "move+right_click"], width=15)
        self.combo_action_pos.grid(row=1, column=1)
        ttk.Label(fpos, text="딜레이(초):", background="#f8fff8").grid(row=1, column=2)
        self.var_delay_pos = tk.DoubleVar(value=0.5)
        tk.Entry(fpos, textvariable=self.var_delay_pos, width=8).grid(row=1, column=3, padx=2)
        tk.Button(poscard, text="좌표 단계 추가", command=self.add_step_pos, height=2, bg="#d3ffe6").pack(pady=4)

        # --- [wait 단계 추가] 카드 ---
        waitcard = Frame(center, bd=2, relief="groove", bg="#fff9e7")
        waitcard.pack(pady=7, fill="x")
        ttk.Label(waitcard, text="WAIT(대기) 단계 추가", background="#fff9e7",
                  font=("맑은 고딕", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        fwait = Frame(waitcard, bg="#fff9e7")
        fwait.pack(padx=7, pady=2, fill="x")
        ttk.Label(fwait, text="대기 시간(초):", background="#fff9e7").grid(row=0, column=0)
        self.var_wait = tk.DoubleVar(value=1.0)
        tk.Entry(fwait, textvariable=self.var_wait, width=8).grid(row=0, column=1, padx=2)
        tk.Button(waitcard, text="wait 단계 추가", command=self.add_step_wait, height=2, bg="#ffeeb0").pack(pady=4)

        # --- [매크로 녹화 카드] ---
        macard = Frame(center, bd=2, relief="groove", bg="#fff8ee")
        macard.pack(pady=7, fill="x")
        ttk.Label(macard, text="마우스 매크로 녹화", background="#fff8ee",
                  font=("맑은 고딕", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        Frame(macard, height=1, bg="#ffe0b2").pack(fill="x", padx=7, pady=2)
        mbtn = Frame(macard, bg="#fff8ee")
        mbtn.pack(pady=2, fill="x")
        tk.Button(mbtn, text="🟢 녹화 시작", command=self.start_macro_record, width=11, bg="#ffe6d6").pack(side="left", padx=6)
        tk.Button(mbtn, text="⏹️ 중지/반영", command=self.stop_macro_record, width=11, bg="#ffe6d6").pack(side="left", padx=6)
        self.label_macro = tk.Label(macard, text="매크로: 준비됨", fg="gray", background="#fff8ee", font=("맑은 고딕", 9))
        self.label_macro.pack(anchor="w", padx=10, pady=3)

        # 3. 우측: 시나리오 리스트
        right = Frame(mainframe)
        right.grid(row=0, column=2, sticky="ns")
        ttk.Label(right, text="시나리오 리스트", font=("맑은 고딕", 11, "bold")).pack(anchor="w", pady=3)
        self.scenario = []
        self.list_scn = tk.Listbox(right, height=27, width=50, selectmode=tk.EXTENDED)
        self.list_scn.pack(pady=4, padx=2, fill="y")

        # 하단: 버튼들
        botbar = Frame(self)
        botbar.pack(fill="x", pady=7)
        tk.Button(botbar, text="▲", command=self.move_up, width=4).pack(side="left", padx=3)
        tk.Button(botbar, text="▼", command=self.move_down, width=4).pack(side="left", padx=3)
        tk.Button(botbar, text="삭제", command=self.del_step_multi, width=8, fg="red").pack(side="left", padx=7)
        tk.Button(botbar, text="실행 ▶", command=self.run_scenario, width=12, font=("맑은 고딕", 12), bg="#faffb0").pack(side="right", padx=8)
        tk.Button(botbar, text="저장", command=self.save_scn, width=8).pack(side="right", padx=3)
        tk.Button(botbar, text="불러오기", command=self.load_scn, width=8).pack(side="right", padx=3)

        self.protocol("WM_DELETE_WINDOW", self.quit)

        # 매크로 녹화 상태
        self.macro_recording = False
        self.macro_events = []
        self.macro_listener = None
        self.macro_last_time = None

    def add_step_img(self):
        sel = self.list_img.curselection()
        if not sel:
            messagebox.showinfo("알림", "이미지 선택 후 추가하세요!")
            return
        fname = self.img_files[sel[0]]
        act = self.var_action_img.get()
        delay = self.var_delay_img.get()
        step = {"type": "img", "img": fname, "action": act, "delay": delay}
        self._insert_step(step)

    def add_step_pos(self):
        x = self.var_x.get()
        y = self.var_y.get()
        act = self.var_action_pos.get()
        delay = self.var_delay_pos.get()
        step = {"type": "pos", "x": x, "y": y, "action": act, "delay": delay}
        self._insert_step(step)

    def add_step_wait(self):
        delay = self.var_wait.get()
        if delay <= 0:
            messagebox.showinfo("알림", "대기 시간은 0보다 커야 합니다.")
            return
        step = {"type": "wait", "delay": delay}
        self._insert_step(step)

    def _insert_step(self, step):
        sel = list(self.list_scn.curselection())
        if sel:
            idx = sel[-1] + 1
            self.scenario.insert(idx, step)
        else:
            self.scenario.append(step)
        self.refresh_scn_list()

    def del_step_multi(self):
        selected = list(self.list_scn.curselection())
        if not selected:
            return
        for idx in reversed(selected):
            if 0 <= idx < len(self.scenario):
                self.scenario.pop(idx)
        self.refresh_scn_list()

    def move_up(self):
        sel = list(self.list_scn.curselection())
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        self.scenario[idx-1], self.scenario[idx] = self.scenario[idx], self.scenario[idx-1]
        self.refresh_scn_list()
        self.list_scn.select_set(idx-1)

    def move_down(self):
        sel = list(self.list_scn.curselection())
        if not sel or sel[0] == len(self.scenario)-1:
            return
        idx = sel[0]
        self.scenario[idx+1], self.scenario[idx] = self.scenario[idx], self.scenario[idx+1]
        self.refresh_scn_list()
        self.list_scn.select_set(idx+1)

    def refresh_scn_list(self):
        self.list_scn.delete(0, tk.END)
        for step in self.scenario:
            if step["type"] == "img":
                self.list_scn.insert(
                    tk.END,
                    f"[IMG] {step['img']} | {step['action']} | {step['delay']}s"
                )
            elif step["type"] == "pos":
                self.list_scn.insert(
                    tk.END,
                    f"[POS] ({step['x']},{step['y']}) | {step['action']} | {step['delay']}s"
                )
            elif step["type"] == "wait":
                self.list_scn.insert(
                    tk.END,
                    f"[WAIT] {round(step['delay'], 3)}s"
                )
        for idx in range(self.list_scn.size()):
            self.list_scn.itemconfig(idx, bg="white", fg="black")

    def save_scn(self):
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not fp:
            return
        with open(fp, "w") as f:
            json.dump(self.scenario, f, indent=2)
        messagebox.showinfo("저장", f"시나리오 저장: {fp}")

    def load_scn(self):
        fp = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not fp:
            return
        with open(fp, "r") as f:
            self.scenario = json.load(f)
        self.refresh_scn_list()

    def run_scenario(self):
        sel_title = self.var_sel.get()
        if not sel_title:
            messagebox.showinfo("에러", "창을 선택하세요!")
            return
        try:
            left, top, w, h = get_window_rect(sel_title)
        except Exception:
            messagebox.showinfo("에러", f"창 위치를 가져올 수 없습니다: {sel_title}")
            return
        if not self.scenario:
            messagebox.showinfo("에러", "실행할 시나리오가 없습니다!")
            return

        for idx in range(self.list_scn.size()):
            self.list_scn.itemconfig(idx, bg="white", fg="black")

        for i, step in enumerate(self.scenario):
            self.list_scn.selection_clear(0, tk.END)
            self.list_scn.selection_set(i)
            self.list_scn.activate(i)
            self.list_scn.see(i)
            self.list_scn.itemconfig(i, bg='yellow', fg='black')
            self.update_idletasks()

            ok = False
            try:
                if step["type"] == "img":
                    img_path = os.path.join(IMG_DIR, step["img"])
                    act = step["action"]
                    delay = step["delay"]
                    result = template_match_in_window(img_path, left, top, w, h, threshold=0.85)
                    if result:
                        fx, fy, conf = result
                        self.do_action(act, fx, fy)
                        ok = True
                    else:
                        self.list_scn.itemconfig(i, bg='#ff5555', fg="black")
                        self.update_idletasks()
                        messagebox.showerror("감지 실패", f"단계 {i+1}: {step['img']} 이미지를 창에서 감지하지 못했습니다.\n시나리오를 중단합니다.")
                        return
                    time.sleep(delay)
                elif step["type"] == "pos":
                    act = step["action"]
                    delay = step["delay"]
                    fx, fy = step["x"], step["y"]
                    self.do_action(act, fx, fy)
                    ok = True
                    time.sleep(delay)
                elif step["type"] == "wait":
                    time.sleep(step["delay"])
                    ok = True
            except Exception as e:
                print("예외 발생:", e)
                messagebox.showerror("실행 중 오류", str(e))
                return

            if ok:
                self.list_scn.itemconfig(i, bg='#cccccc', fg="black")
                self.update_idletasks()
        messagebox.showinfo("완료", f"시나리오 자동 실행 완료!")

    def do_action(self, act, fx, fy):
        if act == "move":
            pyautogui.moveTo(fx, fy, duration=0)
        elif act == "click":
            pyautogui.moveTo(fx, fy, duration=0)
            pyautogui.click()
        elif act == "right_click":
            pyautogui.moveTo(fx, fy, duration=0)
            pyautogui.rightClick()
        elif act == "move+click":
            pyautogui.moveTo(fx, fy, duration=0)
            pyautogui.click()
        elif act == "move+right_click":
            pyautogui.moveTo(fx, fy, duration=0)
            pyautogui.rightClick()
        else:
            pass

    # === 매크로 녹화 (진짜 멈춤만 wait) ===
    def start_macro_record(self):
        if self.macro_recording:
            messagebox.showinfo("알림", "이미 녹화 중입니다!")
            return
        self.label_macro.config(text="녹화 중: 마우스 이동/클릭/우클릭 기록됨", fg="red")
        self.macro_recording = True
        self.macro_events = []
        self.macro_last_time = time.time()

        def on_move(x, y):
            now = time.time()
            self.macro_events.append({'type': 'move', 'x': x, 'y': y, 'abs_time': now})
            self.macro_last_time = now

        def on_click(x, y, button, pressed):
            if pressed: return
            now = time.time()
            act = 'click' if button.name == 'left' else 'right_click'
            self.macro_events.append({'type': act, 'x': x, 'y': y, 'abs_time': now})
            self.macro_last_time = now

        self.macro_listener = mouse.Listener(on_move=on_move, on_click=on_click)
        self.macro_listener.start()

    def stop_macro_record(self):
        if not self.macro_recording:
            messagebox.showinfo("알림", "녹화를 먼저 시작하세요!")
            return
        self.macro_recording = False
        try:
            if self.macro_listener:
                self.macro_listener.stop()
        except Exception:
            pass
        self.label_macro.config(text=f"녹화된 액션: {len(self.macro_events)}개", fg="gray")

        filtered = []
        WAIT_THRESHOLD = 0.15  # 0.15초 이상 멈춘 경우만 wait
        last_time = None

        for idx, ev in enumerate(self.macro_events):
            now = ev['abs_time']
            if last_time is not None:
                gap = now - last_time
                if gap > WAIT_THRESHOLD:
                    filtered.append({"type": "wait", "delay": gap})
            # move는 연속 마지막만 남기고, click/right_click은 모두 남김
            if ev["type"] == "move":
                if idx+1 == len(self.macro_events) or self.macro_events[idx+1]["type"] != "move":
                    filtered.append({
                        "type": "pos",
                        "x": ev["x"],
                        "y": ev["y"],
                        "action": "move",
                        "delay": 0
                    })
            elif ev["type"] in ("click", "right_click"):
                filtered.append({
                    "type": "pos",
                    "x": ev["x"],
                    "y": ev["y"],
                    "action": ev["type"],
                    "delay": 0
                })
            last_time = now

        self.scenario += filtered
        self.refresh_scn_list()
        messagebox.showinfo("녹화 완료", f"손을 멈춘 시간만 wait, move 중복 없음, click/우클릭 반영됨!\n({len(filtered)}개 단계)")

    def quit(self):
        try:
            if hasattr(self, "macro_listener") and self.macro_listener:
                self.macro_listener.stop()
        except Exception:
            pass
        self.destroy()

if __name__ == "__main__":
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)
    app = ScenarioApp()
    app.mainloop()
