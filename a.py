import win32gui
import win32api
import win32con
import pygetwindow as gw
import time

MAIN_WINDOW_KEYWORD = "Naver"
SUB_WINDOW_KEYWORD = "Hecto"

click_sync_enabled = True
toggle_held = False  # prevent double toggling on button hold

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
    time.sleep(0.08)  # ⏱️ 부캐릭 창 클릭 전 약간 대기 (메인 클릭 안정화)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(0.08)  # ⏱️ 클릭 유지 시간 늘림
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def main():
    global click_sync_enabled, toggle_held

    print("▶ 클릭 동기화 시작 (XBUTTON2로 토글, Ctrl+C로 종료)\n")

    main_win = find_window_by_title(MAIN_WINDOW_KEYWORD)
    sub_win = find_window_by_title(SUB_WINDOW_KEYWORD)

    if not main_win or not sub_win:
        print("❌ 메인 또는 부캐 창을 찾을 수 없습니다.")
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
        if win32api.GetKeyState(6) < 0:  # XBUTTON2
            if not toggle_held:
                click_sync_enabled = not click_sync_enabled
                print(f"[동기화 상태 전환됨] {'ON' if click_sync_enabled else 'OFF'}")
                toggle_held = True
        else:
            toggle_held = False

        if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
            now = time.time()
            if now - last_click_time > 0.3:
                if not click_sync_enabled:
                    print("[⏸️ 무시됨] 동기화 OFF 상태")
                    time.sleep(0.1)
                    continue

                click_x, click_y = win32api.GetCursorPos()
                rel_x = click_x - main_left
                rel_y = click_y - main_top

                if rel_x < 0 or rel_y < 0 or rel_x > main_width or rel_y > main_height:
                    print(f"[⛔ 무시됨] 메인 창 바깥 클릭: ({click_x}, {click_y})")
                    continue

                target_x = sub_left + rel_x
                target_y = sub_top + rel_y

                print(f"\n[🖱️ 클릭 감지]")
                print(f"  [메인 창] 클릭: ({click_x}, {click_y}) → 상대: ({rel_x}, {rel_y})")
                print(f"  [부캐 창] 적용 좌표: ({target_x}, {target_y})")

                send_click_absolute(sub_hwnd, target_x, target_y)
                last_click_time = now

        time.sleep(0.01)

if __name__ == "__main__":
    main()
