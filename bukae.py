import win32gui
import win32api
import win32con
import time
import pygetwindow as gw

MAIN_WINDOW_KEYWORD = "dy"
SUB_WINDOW_KEYWORD = "dj"

click_sync_enabled = True
toggle_held = False  # 마우스 버튼 누름 상태 추적 (중복 토글 방지)

def get_window_rect(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right - left, bottom - top

def screen_to_client(hwnd, screen_x, screen_y):
    point = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
    return point  # (x, y)

def find_window_by_title(keyword):
    for w in gw.getWindowsWithTitle(''):
        if keyword.lower() in w.title.lower():
            return w
    return None

def send_click(hwnd, client_x, client_y):
    lParam = win32api.MAKELONG(client_x, client_y)
    print(f"✅ 부캐릭 클릭: hwnd={hwnd}, 클라이언트 좌표=({client_x},{client_y})")
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    time.sleep(0.05)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def main():
    global click_sync_enabled, toggle_held

    print("▶ 클라이언트 좌표 기반 클릭 동기화 시작 (마우스 XBUTTON2로 ON/OFF, Ctrl+C 종료)\n")

    main_win = find_window_by_title(MAIN_WINDOW_KEYWORD)
    sub_win = find_window_by_title(SUB_WINDOW_KEYWORD)

    if not main_win or not sub_win:
        print("❌ 메인 또는 부캐 창을 찾을 수 없습니다.")
        return

    main_hwnd = main_win._hWnd
    sub_hwnd = sub_win._hWnd

    main_left, main_top, main_width, main_height = get_window_rect(main_hwnd)
    sub_left, sub_top, sub_width, sub_height = get_window_rect(sub_hwnd)

    print(f"📐 메인 창 위치: ({main_left}, {main_top}), 크기: {main_width}x{main_height}")
    print(f"📐 부캐 창 위치: ({sub_left}, {sub_top}), 크기: {sub_width}x{sub_height}")
    print(f"🔁 클릭 동기화 상태: {'ON' if click_sync_enabled else 'OFF'}")

    last_click_time = 0

    while True:
        # 🔁 XBUTTON2 토글 감지 (6번 키)
        if win32api.GetKeyState(5) < 0:
            if not toggle_held:
                click_sync_enabled = not click_sync_enabled
                print(f"\n🔁 클릭 동기화 상태 전환됨 → {'ON' if click_sync_enabled else 'OFF'}")
                toggle_held = True
        else:
            toggle_held = False

        # 🖱️ 마우스 클릭 감지
        if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
            now = time.time()
            if now - last_click_time > 0.3:
                if not click_sync_enabled:
                    print("⏸️ 동기화 OFF 상태 — 클릭 무시")
                    time.sleep(0.1)
                    continue

                click_x, click_y = win32api.GetCursorPos()

                rel_x = click_x - main_left
                rel_y = click_y - main_top

                if rel_x < 0 or rel_y < 0 or rel_x > main_width or rel_y > main_height:
                    print("⛔ 클릭이 메인 창 영역을 벗어났습니다. 무시합니다.")
                    continue

                print(f"\n🖱️ 클릭 스크린 좌표: ({click_x}, {click_y})")
                print(f"📍 상대좌표 (메인 기준): ({rel_x}, {rel_y})")

                sub_client_x, sub_client_y = screen_to_client(sub_hwnd, click_x, click_y)
                print(f"📐 계산식: ScreenToClient({click_x},{click_y}) => ({sub_client_x},{sub_client_y})")

                send_click(sub_hwnd, sub_client_x, sub_client_y)

                last_click_time = now

        time.sleep(0.01)

if __name__ == "__main__":
    main()
