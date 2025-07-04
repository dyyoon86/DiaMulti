import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import pygetwindow as gw
import pyautogui
import cv2
import numpy as np
import os
import json
import time

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
        self.title("시나리오 빌더 & 자동 실행기")
        self.geometry("800x400")
        self.win_titles = get_window_list()
        self.var_sel = tk.StringVar(value=self.win_titles[0] if self.win_titles else "")
        ttk.Label(self, text="대상 창 선택:").grid(row=0, column=0, padx=8)
        self.combo = ttk.Combobox(self, textvariable=self.var_sel, values=self.win_titles, width=50)
        self.combo.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4)

        # 이미지 리스트
        self.img_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(".png")]
        ttk.Label(self, text="img/ 이미지 목록").grid(row=1, column=0)
        self.list_img = tk.Listbox(self, height=16, width=36)
        for f in self.img_files:
            self.list_img.insert(tk.END, f)
        self.list_img.grid(row=2, column=0, rowspan=4, padx=8, pady=8)

        # 시나리오 리스트
        ttk.Label(self, text="시나리오 단계").grid(row=1, column=2)
        self.scenario = []
        self.list_scn = tk.Listbox(self, height=16, width=45)
        self.list_scn.grid(row=2, column=2, rowspan=4, padx=8, pady=8)

        # 행동 선택
        self.var_action = tk.StringVar(value="move")
        self.combo_action = ttk.Combobox(self, textvariable=self.var_action, values=["move", "move+click"], width=14)
        self.combo_action.grid(row=2, column=1, sticky="n", padx=2)
        # 딜레이 입력
        self.var_delay = tk.DoubleVar(value=0.5)
        ttk.Label(self, text="딜레이(초):").grid(row=3, column=1, sticky="w")
        tk.Entry(self, textvariable=self.var_delay, width=8).grid(row=3, column=1, sticky="e")

        # 추가/삭제/순서변경
        tk.Button(self, text="추가", command=self.add_step).grid(row=4, column=1, pady=2)
        tk.Button(self, text="삭제", command=self.del_step).grid(row=5, column=1, pady=2)
        tk.Button(self, text="▲", command=self.move_up).grid(row=4, column=3)
        tk.Button(self, text="▼", command=self.move_down).grid(row=5, column=3)

        # 저장/불러오기
        tk.Button(self, text="저장", command=self.save_scn).grid(row=6, column=2, sticky="e", padx=8)
        tk.Button(self, text="불러오기", command=self.load_scn).grid(row=6, column=2, sticky="w", padx=8)
        # 실행 버튼
        tk.Button(self, text="실행 ▶", command=self.run_scenario, font=("Arial", 14), bg="yellow").grid(row=6, column=0, pady=4)

        self.protocol("WM_DELETE_WINDOW", self.quit)

    def add_step(self):
        sel = self.list_img.curselection()
        if not sel:
            messagebox.showinfo("알림", "이미지 선택 후 추가하세요!")
            return
        fname = self.img_files[sel[0]]
        act = self.var_action.get()
        delay = self.var_delay.get()
        step = {"img": fname, "action": act, "delay": delay}
        self.scenario.append(step)
        self.refresh_scn_list()

    def del_step(self):
        sel = self.list_scn.curselection()
        if not sel:
            return
        idx = sel[0]
        self.scenario.pop(idx)
        self.refresh_scn_list()

    def move_up(self):
        sel = self.list_scn.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        self.scenario[idx-1], self.scenario[idx] = self.scenario[idx], self.scenario[idx-1]
        self.refresh_scn_list()
        self.list_scn.select_set(idx-1)

    def move_down(self):
        sel = self.list_scn.curselection()
        if not sel or sel[0] == len(self.scenario)-1:
            return
        idx = sel[0]
        self.scenario[idx+1], self.scenario[idx] = self.scenario[idx], self.scenario[idx+1]
        self.refresh_scn_list()
        self.list_scn.select_set(idx+1)

    def refresh_scn_list(self):
        self.list_scn.delete(0, tk.END)
        for step in self.scenario:
            self.list_scn.insert(tk.END, f"{step['img']} | {step['action']} | {step['delay']}s")

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
        for i, step in enumerate(self.scenario):
            img_path = os.path.join(IMG_DIR, step["img"])
            act = step["action"]
            delay = step["delay"]
            print(f"[{i+1}/{len(self.scenario)}] {step['img']} 템플릿 감지중...")
            result = template_match_in_window(img_path, left, top, w, h, threshold=0.85)
            if result:
                fx, fy, conf = result
                print(f" → {act.upper()} ({fx},{fy}) | 신뢰도: {conf:.2f}")
                pyautogui.moveTo(fx, fy, duration=0)
                if act == "move+click":
                    pyautogui.click()
                time.sleep(delay)
            else:
                print(" → 감지 실패. 대기 중...")
                time.sleep(delay)
        messagebox.showinfo("완료", f"시나리오 자동 실행 완료!")

    def quit(self):
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    if not os.path.exists(IMG_DIR):
        os.makedirs(IMG_DIR)
    app = ScenarioApp()
    app.mainloop()
