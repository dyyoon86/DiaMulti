import tkinter as tk
from tkinter import ttk, messagebox
import pygetwindow as gw
import pyautogui
from PIL import Image
import cv2
import numpy as np
import os
import time

def get_window_list():
    return [w for w in gw.getAllTitles() if w.strip()]

def get_window_rect(title):
    win = gw.getWindowsWithTitle(title)[0]
    return win.left, win.top, win.width, win.height

def template_match_in_window(img_path, left, top, w, h, threshold=0.85):
    """해당 창(left,top,w,h) 영역에서 img_path 템플릿 찾기"""
    # 1. 창 영역 스크린샷
    scr = pyautogui.screenshot(region=(left, top, w, h))
    scr_np = np.array(scr)
    img_gray = cv2.cvtColor(scr_np, cv2.COLOR_BGR2GRAY)
    # 2. 템플릿 이미지 로드
    template = cv2.imread(img_path, 0)
    if template is None:
        return None
    th, tw = template.shape
    # 3. 템플릿 매칭
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        # 실제 모니터 전체 좌표 반환 (윈도우좌상단 + 템플릿 위치)
        found_x = left + max_loc[0] + tw // 2
        found_y = top + max_loc[1] + th // 2
        return (found_x, found_y, max_val)
    return None

class FinderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("이미지 위치 찾기 & 마우스 이동")
        self.geometry("450x140")
        self.win_titles = get_window_list()
        self.var_sel = tk.StringVar(value=self.win_titles[0] if self.win_titles else "")
        self.combo = ttk.Combobox(self, textvariable=self.var_sel, values=self.win_titles, width=45)
        self.combo.pack(pady=8)
        self.btn_start = tk.Button(self, text="img 폴더 전체 이미지 → 감지&마우스이동", command=self.find_and_move)
        self.btn_start.pack(pady=6)
        self.protocol("WM_DELETE_WINDOW", self.quit)

    def find_and_move(self):
        sel_title = self.var_sel.get()
        if not sel_title:
            messagebox.showinfo("에러", "창을 선택하세요!")
            return
        try:
            left, top, w, h = get_window_rect(sel_title)
        except Exception:
            messagebox.showinfo("에러", f"창 위치를 가져올 수 없습니다: {sel_title}")
            return

        img_dir = os.path.abspath("img")
        if not os.path.exists(img_dir):
            messagebox.showinfo("에러", f"이미지 폴더가 없습니다: {img_dir}")
            return
        img_files = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if f.lower().endswith('.png')]
        if not img_files:
            messagebox.showinfo("에러", f"img 폴더에 PNG 이미지가 없습니다.")
            return

        for i, img_path in enumerate(img_files):
            print(f"[{i+1}/{len(img_files)}] {os.path.basename(img_path)} 템플릿 찾기...")
            result = template_match_in_window(img_path, left, top, w, h, threshold=0.85)
            if result:
                fx, fy, conf = result
                print(f" → 찾음! ({fx},{fy}) | 신뢰도: {conf:.2f}")
                pyautogui.moveTo(fx, fy)
                time.sleep(1.2)
            else:
                print(f" → 못 찾음.")
                time.sleep(0.7)
        messagebox.showinfo("완료", f"모든 이미지에 대해 마우스 이동 완료!")

    def quit(self):
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = FinderApp()
    app.mainloop()
