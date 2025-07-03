import win32gui
import win32api
import win32con
import time
import pygetwindow as gw

MAIN_WINDOW_KEYWORD = "NA"
SUB_WINDOW_KEYWORD = "He"

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

def map_click_to_sub_window(main_rect, sub_rect, click_point):
    """
    main 창에서 클릭한 위치를 기준으로,
    sub 창에서 같은 위치(상대적 비율)를 구하여 스크린 절대좌표로 반환
    """
    main_left, main_top, main_width, main_height = main_rect
    sub_left, sub_top, sub_width, sub_height = sub_rect
    click_x, click_y = click_point

    # 1. 메인 기준 상대 위치
    rel_x = click_x - main_left
    rel_y = click_y - main_top

    if rel_x < 0 or rel_y < 0 or rel_x > main_width or rel_y > main_height:
        print("❌ 클릭이 메인 창을 벗어났습니다.")
        return None

    # 2. 상대 비율 계산
    ratio_x = rel_x / main_width
    ratio_y = rel_y / main_height

    # 3. Sub 창의 동일 비율 위치 (스크린 절대 좌표)
    sub_click_x = int(sub_left + ratio_x * sub_width)
    sub_click_y = int(sub_top + ratio_y * sub_height)

    return sub_click_x, sub_click_y

def map_main_click_to_sub_client(main_rect, sub_rect, click_point):
    """
    메인창 기준 클릭 위치를 부캐 창 기준 클라이언트 좌표로 변환
    """
    main_left, main_top, main_width, main_height = main_rect
    sub_left, sub_top, sub_width, sub_height = sub_rect
    click_x, click_y = click_point

    # 1. 메인 기준 상대좌표
    rel_x = click_x - main_left
    rel_y = click_y - main_top

    if rel_x < 0 or rel_y < 0 or rel_x > main_width or rel_y > main_height:
        print("❌ 클릭이 메인 창 영역을 벗어났습니다.")
        return None

    # 2. 상대 위치의 비율 계산
    ratio_x = rel_x / main_width
    ratio_y = rel_y / main_height

    # 3. 부캐창 클라이언트 좌표계 기준으로 환산
    client_x = int(ratio_x * sub_width)
    client_y = int(ratio_y * sub_height)

    return client_x, client_y


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

                #sub_client_x, sub_client_y = screen_to_client(sub_hwnd, click_x, click_y)

                main_rect = (main_left, main_top, main_width, main_height)
                sub_rect = (sub_left, sub_top, sub_width, sub_height)
                click_point = (click_x, click_y)
                sub_client_x, sub_client_y = map_main_click_to_sub_client(main_rect, sub_rect , click_point )
                print(f"📐 계산식: ScreenToClient({click_x},{click_y}) => ({sub_client_x},{sub_client_y})")

                send_click(sub_hwnd, sub_client_x, sub_client_y)

                last_click_time = now

        time.sleep(0.01)

if __name__ == "__main__":
    main()

"""

 ▶ 클라이언트 좌표 기반 클릭 동기화 시작 (마우스 XBUTTON2로 ON/OFF, Ctrl+C 종료)

 📐 메인 창 위치: (-7, 0), 크기: 974x1047
 📐 부캐 창 위치: (953, 0), 크기: 974x1047
 🔁 클릭 동기화 상태: ON

 🖱️ 클릭 스크린 좌표: (454, 59)
 📍 상대좌표 (메인 기준): (461, 59)
 📐 계산식: ScreenToClient(454,59) => (-507,59)
 ✅ 부캐릭 클릭: hwnd=4851256, 클라이언트 좌표=(-507,59)


 """