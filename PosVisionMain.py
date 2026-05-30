import cv2
import numpy as np
import platform
import subprocess
import sys
from utils import (
    fps_counter, correct_mm, generate_line, load_selection, get_error,
    CameraStream, AppState, build_screen,
    exit_button_coord, start_button_coord,
    set_error_color, WinCameraStream,
    sine_button_coord, tri_button_coord,
    line_button_coord,
    terminate_button_coord, cal_button_coord
)

# ── Constants ─────────────────────────────────────────────────────────────────
LOWER_GREEN = (35,  80, 100)
UPPER_GREEN = (85, 255, 255)
HIGHLIGHT   = [255, 0, 255]

# ── Setup ─────────────────────────────────────────────────────────────────────
menu_wallpaper = cv2.imread("wallpaper.png", cv2.IMREAD_COLOR)
wallpaper = cv2.imread("Main_UI.png", cv2.IMREAD_COLOR)
fps100    = fps_counter(100)

if platform.system() == "Linux":
    stream         = CameraStream()
else:
    stream         = WinCameraStream()

width, height  = stream.width, stream.height

calib_data = np.load("calib_data.npz")
H          = np.load("homography_matrix.npy")
H_inv      = np.linalg.inv(H)
mtx        = calib_data["mtx"]
dist       = calib_data["dist"]

state = AppState()

# ── UI Callback ───────────────────────────────────────────────────────────────
def click_event(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if state.menu:
        if sine_button_coord[0] <= x <= sine_button_coord[2] and sine_button_coord[1] <= y <= sine_button_coord[3]:
            state.setpoints = load_selection("sine")
            state.menu = False
        elif tri_button_coord[0] <= x <= tri_button_coord[2] and tri_button_coord[1] <= y <= tri_button_coord[3]:
            state.setpoints = load_selection("triangle")
            state.menu = False
        elif line_button_coord[0] <= x <= line_button_coord[2] and line_button_coord[1] <= y <= line_button_coord[3]:
            state.setpoints = load_selection("line")
            state.menu = False
        elif cal_button_coord[0] <= x <= cal_button_coord[2] and cal_button_coord[1] <= y <= cal_button_coord[3]:
            proc = subprocess.Popen([sys.executable, "/home/user/Pen-position-vision/homography.py"])
            proc.wait()   # waits until second script closes
        elif terminate_button_coord[0] <= x <= terminate_button_coord[2] and terminate_button_coord[1] <= y <= terminate_button_coord[3]:
            state.running = False           # stop loop
    else:
        if exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
            state.__init__()

        elif start_button_coord[0] <= x <= start_button_coord[2] and start_button_coord[1] <= y <= start_button_coord[3]:
            if state.avg_x is not None and state.avg_y is not None:
                state.offset_x    = state.avg_x
                state.offset_y    = state.avg_y
                state.offset_mm_x, state.offset_mm_y = correct_mm(state.avg_x, state.avg_y, mtx, dist, H)
                state.drawn_overlay = np.zeros((480, 640, 3), dtype=np.uint8)
                state.line_overlay  = generate_line(state.offset_x, state.offset_y, H_inv, state.setpoints)
                state.started = True

# ── Window ────────────────────────────────────────────────────────────────────
cv2.namedWindow("Camera", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Camera", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Camera", click_event)

# ── Main Loop ─────────────────────────────────────────────────────────────────
while state.running:
    if state.menu:
        cv2.imshow("Camera", menu_wallpaper)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    else:
        frame     = stream.read()
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        fps100.tick()

        # Detection
        mask            = cv2.inRange(frame_hsv, LOWER_GREEN, UPPER_GREEN)
        frame[mask > 0] = HIGHLIGHT

        # Composite frame + UI
        final_screen = build_screen(frame, state.line_overlay, state.drawn_overlay, wallpaper)
        cv2.putText(final_screen, f"{fps100.avg_fps:.1f}", (100, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # Marker position
        M = cv2.moments(mask)
        if M["m00"] > 0:
            state.avg_x = int(M["m10"] / M["m00"])
            state.avg_y = int(M["m01"] / M["m00"])
            mm_x, mm_y     = correct_mm(state.avg_x, state.avg_y, mtx, dist, H)
            corrected_mm_x = mm_x - state.offset_mm_x
            corrected_mm_y = mm_y - state.offset_mm_y
            if state.prev_point is not None and state.started:
                error = get_error(state.setpoints, corrected_mm_x, corrected_mm_y)
                color = set_error_color(error)
                cv2.line(state.drawn_overlay, state.prev_point, (state.avg_x, state.avg_y), color, 3)
                cv2.putText(final_screen, f"{error:.1f}", (400, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            state.prev_point = (state.avg_x, state.avg_y)

        cv2.imshow("Camera", final_screen)
        if cv2.waitKey(1) & 0xFF == 27:
            break

stream.stop()
cv2.destroyAllWindows()
