import win32gui
import win32api
import win32con
import pygetwindow as gw
import time
import tkinter as tk
import threading
import sys
import traceback

MAIN_WINDOW_KEYWORD = "NAVER"
SUB_WINDOW_KEYWORD = "Hecto"

click_sync_enabled = True
toggle_held = False

class ClickOverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.configure(bg='white')
        self.wm_attributes("-transparentcolor", "white")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.canvas = tk.Canvas(self, width=self.winfo_screenwidth(), height=self.winfo_screenheight(),
                                bg='white', highlightthickness=0)
        self.canvas.pack()
        self.dot = None

    def draw_dot(self, x, y):
        if self.dot:
            self.canvas.delete(self.dot)
        self.dot = self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="red")
        self.after(500, lambda: self.canvas.delete(self.dot))

def get_window_rect(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right - left, bottom - top

def screen_to_client(hwnd, screen_x, screen_y):
    return win32gui.ScreenToClient(hwnd, (screen_x, screen_y))

def find_window_by_title(keyword):
    for w in gw.getWindowsWithTitle(''):
        if keyword.lower() in w.title.lower():
            return w
    return None

def send_click_absolute(hwnd, screen_x, screen_y):
    client_x, client_y = screen_to_client(hwnd, screen_x, screen_y)
    lParam = win32api.MAKELONG(client_x, client_y)
    print(f"[SEND CLICK] Screen: ({screen_x}, {screen_y}) → Client: ({client_x}, {client_y})")
    time.sleep(0.08)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(0.08)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def click_sync_loop(overlay):
    global click_sync_enabled, toggle_held
    try:
        print("▶ v2: 동기화 시작 (XBUTTON2 토글 / Ctrl+Shift+X 종료)\n")

        main_win = find_window_by_title(MAIN_WINDOW_KEYWORD)
        sub_win = find_window_by_title(SUB_WINDOW_KEYWORD)

        if not main_win or not sub_win:
            print("❌ 메인 또는 부캐 창을 찾을 수 없습니다.")
            overlay.quit()
            return

        main_hwnd = main_win._hWnd
        sub_hwnd = sub_win._hWnd

        main_left, main_top, main_width, main_height = get_window_rect(main_hwnd)
        sub_left, sub_top, sub_width, sub_height = get_window_rect(sub_hwnd)

        print(f"[메인 창] 위치=({main_left}, {main_top}) 크기={main_width}x{main_height}")
        print(f"[부캐 창] 위치=({sub_left}, {sub_top}) 크기={sub_width}x{sub_height}")
        print(f"[동기화 상태] {'ON' if click_sync_enabled else 'OFF'}")

        last_click_time = 0

        while True:
            # 종료 키: Ctrl + Shift + X
            ctrl = win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000
            shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
            xkey = win32api.GetAsyncKeyState(ord('X')) & 0x8000
            if ctrl and shift and xkey:
                print("❌ Ctrl+Shift+X → 종료")
                overlay.quit()
                overlay.destroy()
                sys.exit()

            # 동기화 토글
            if win32api.GetKeyState(6) < 0:  # XBUTTON2
                if not toggle_held:
                    click_sync_enabled = not click_sync_enabled
                    print(f"[동기화 상태] {'ON' if click_sync_enabled else 'OFF'}")
                    toggle_held = True
            else:
                toggle_held = False

            if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
                now = time.time()
                if now - last_click_time > 0.3:
                    if not click_sync_enabled:
                        time.sleep(0.1)
                        continue

                    click_x, click_y = win32api.GetCursorPos()
                    rel_x = click_x - main_left
                    rel_y = click_y - main_top

                    if rel_x < 0 or rel_y < 0 or rel_x > main_width or rel_y > main_height:
                        print(f"[⛔ 무시됨] 메인 창 밖 클릭 ({click_x},{click_y})")
                        continue

                    ratio_x = rel_x / main_width
                    ratio_y = rel_y / main_height

                    target_x = sub_left + int(ratio_x * sub_width)
                    target_y = sub_top + int(ratio_y * sub_height)

                    print(f"\n🖱️ 클릭 감지")
                    print(f"  [메인] 상대=({rel_x}, {rel_y}) 비율=({ratio_x:.2%}, {ratio_y:.2%})")
                    print(f"  [부캐] 스크린 좌표=({target_x}, {target_y})")

                    send_click_absolute(sub_hwnd, target_x, target_y)
                    overlay.draw_dot(target_x, target_y)
                    last_click_time = now

            time.sleep(0.01)

    except Exception:
        print("💥 예외 발생:")
        print(traceback.format_exc())
        overlay.quit()
        overlay.destroy()
        sys.exit()

if __name__ == "__main__":
    overlay = ClickOverlay()
    threading.Thread(target=click_sync_loop, args=(overlay,), daemon=True).start()
    overlay.mainloop()
