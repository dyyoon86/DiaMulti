import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pygetwindow as gw
import pyautogui
from PIL import Image, ImageTk
import os
import time

def get_window_list():
    return [w for w in gw.getAllTitles() if w.strip()]

def get_window_rect(title):
    win = gw.getWindowsWithTitle(title)[0]
    return win.left, win.top, win.width, win.height

class CropCaptureTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("드래그영역 템플릿 캡처 툴")
        self.geometry("420x150")
        self.win_titles = get_window_list()
        self.var_sel = tk.StringVar(value=self.win_titles[0] if self.win_titles else "")
        self.combo = ttk.Combobox(self, textvariable=self.var_sel, values=self.win_titles, width=45)
        self.combo.pack(pady=8)
        self.btn_start = tk.Button(self, text="감시 시작", command=self.start_watch)
        self.btn_start.pack()
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.watcher_win = None

    def start_watch(self):
        sel_title = self.var_sel.get()
        if not sel_title:
            messagebox.showinfo("에러", "창을 선택하세요!")
            return
        try:
            left, top, w, h = get_window_rect(sel_title)
        except Exception:
            messagebox.showinfo("에러", f"창 위치를 가져올 수 없습니다: {sel_title}")
            return
        self.withdraw()
        self.watcher_win = CropWatcherWindow(sel_title, left, top, w, h, self)
        self.watcher_win.mainloop()

    def quit(self):
        try:
            if self.watcher_win:
                self.watcher_win.destroy()
        except Exception:
            pass
        self.destroy()
        os._exit(0)  # 프로그램 완전 종료

class CropWatcherWindow(tk.Toplevel):
    def __init__(self, title, left, top, w, h, master):
        super().__init__(master)
        self.title(f"영역 드래그 캡처: {title}")
        self.geometry(f"{w}x{h+90}")
        self.left, self.top, self.w, self.h = left, top, w, h

        self.canvas = tk.Canvas(self, width=w, height=h)
        self.canvas.pack()
        self.label_info = tk.Label(self, text="[드래그로 영역 지정 → 캡처]", font=("Arial", 12))
        self.label_info.pack()
        self.btn_capture = tk.Button(self, text="캡처", command=self.capture_crop, font=("Arial", 16), bg="yellow")
        self.btn_capture.pack(pady=4)
        # --- 저장 경로 수정
        self.save_dir = os.path.abspath("img")
        os.makedirs(self.save_dir, exist_ok=True)
        # ---

        self.rect = None
        self.start_x = self.start_y = self.end_x = self.end_y = None
        self.crop_box = None
        self.img = None
        self.imgtk = None

        self.running = True
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.after(100, self.update_screen)

    def update_screen(self):
        if not self.running:
            return
        img = pyautogui.screenshot(region=(self.left, self.top, self.w, self.h))
        self.img = img
        self.imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.imgtk)
        if self.crop_box:
            self.draw_rect()
        self.after(150, self.update_screen)

    def on_mouse_down(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.end_x, self.end_y = event.x, event.y
        self.crop_box = None
        self.draw_rect()

    def on_mouse_drag(self, event):
        self.end_x, self.end_y = event.x, event.y
        self.draw_rect()

    def on_mouse_up(self, event):
        self.end_x, self.end_y = event.x, event.y
        x0, y0 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
        x1, y1 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
        if abs(x1 - x0) < 5 or abs(y1 - y0) < 5:
            self.crop_box = None
        else:
            self.crop_box = (x0, y0, x1, y1)
        self.draw_rect()

    def draw_rect(self):
        self.canvas.delete("rect")
        if self.crop_box:
            x0, y0, x1, y1 = self.crop_box
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="red", width=2, tag="rect")

    def capture_crop(self):
        if not self.crop_box or not self.img:
            messagebox.showinfo("영역 없음", "드래그로 캡처할 영역을 지정하세요!")
            return
        state_name = simpledialog.askstring("상태 이름", "상태/설명 (ex: portal, town, inv):", initialvalue=f"state_{int(time.time())}")
        if not state_name:
            return
        filename = f"{state_name}_{int(time.time())}.png"
        x0, y0, x1, y1 = self.crop_box
        crop_img = self.img.crop((x0, y0, x1, y1))
        save_path = os.path.join(self.save_dir, filename)
        crop_img.save(save_path)
        messagebox.showinfo("저장 완료", f"영역 PNG 저장됨!\n{save_path}")

    def close(self):
        self.running = False
        self.destroy()
        os._exit(0)   # 감시창 닫아도 프로그램 완전 종료

if __name__ == "__main__":
    app = CropCaptureTool()
    app.mainloop()
