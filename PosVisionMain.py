import cv2
import numpy as np
import platform
import struct
from utils import (
    fps_counter, correct_mm, generate_line, load_selection,
    CameraStream, serial_comms, dummy_serial, AppState, build_screen,
    exit_button_coord, start_button_coord,
    set_error_color, WinCameraStream,
    error_tool,
    sine_button_coord, tri_button_coord,
    line_button_coord,
    terminate_button_coord,
    reset_button_coord, pause_button_coord,
    imu_cal_button_coord
)

# ── Constants ─────────────────────────────────────────────────────────────────
LOWER_GREEN = (50,  80, 110)
UPPER_GREEN = (75, 255, 255)
HIGHLIGHT   = [255, 0, 255]

# ── Setup ─────────────────────────────────────────────────────────────────────
# Load UI assets
menu_wallpaper = cv2.imread("wallpaper.png", cv2.IMREAD_COLOR)
wallpaper = cv2.imread("Main_UI.png", cv2.IMREAD_COLOR)
fps100    = fps_counter(100)
# Disable serial for testing without hardware
no_serial = False
# Select correct camera and serial classes based on OS
if platform.system() == "Linux":
    stream         = CameraStream()
    if no_serial:
        ser = dummy_serial()
    else:
        ser            = serial_comms(port='/dev/ttyACM0')
else:
    stream         = WinCameraStream()
    ser            = dummy_serial()
# Save camera resolution for later use
width, height  = stream.width, stream.height
# Init error value for display
error = 0.0
# Load calibration data
calib_data = np.load("calib_data.npz")
H          = np.load("homography_matrix.npy")
H_inv      = np.linalg.inv(H)
mtx        = calib_data["mtx"]
dist       = calib_data["dist"]
# Init state object and error calculator
state = AppState()
error_cal = error_tool()


# ── UI Callback ───────────────────────────────────────────────────────────────
def click_event(event, x, y, flags, param):
    # Only respond to left clicks
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    # Try to start serial connection if not already connected
    if ser.connected == False:
        ser.start()
    # Handle selection menu clicks
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
        elif terminate_button_coord[0] <= x <= terminate_button_coord[2] and terminate_button_coord[1] <= y <= terminate_button_coord[3]:
            state.running = False           # stop loop
    # Handle main UI clicks
    else:
        if exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
            # Send stop command
            ser.write(bytes(5))
            # Reset all state variables to default
            state.__init__()
        elif start_button_coord[0] <= x <= start_button_coord[2] and start_button_coord[1] <= y <= start_button_coord[3]:
            # Check if marker has been detcted and serial is running
            if state.prev_point is not None and ser.ready:
                if not state.paused:
                    error_cal.reset()
                    state.offset_x    = state.avg_x
                    state.offset_y    = state.avg_y
                    state.offset_mm_x, state.offset_mm_y = correct_mm(state.avg_x, state.avg_y, mtx, dist, H)
                    # Reset drawn overlay
                    state.drawn_overlay = np.zeros((480, 640, 3), dtype=np.uint8)
                    # Generate line overlay based on setpoints and current position
                    state.line_overlay  = generate_line(state.offset_x, state.offset_y, H, H_inv, state.setpoints)
                    state.started = True
                else:
                    state.paused = False
        elif imu_cal_button_coord[0] <= x <= imu_cal_button_coord[2] and imu_cal_button_coord[1] <= y <= imu_cal_button_coord[3]:
            # 0000 0(cal)(reset)(start)
            # send cal command and keep current started state
            cmd = (1 << 2) | (state.started << 0)
            packet = bytes([cmd]) + bytes(4)
            print("CAL command sent")
            ser.write(packet)
        elif pause_button_coord[0] <= x <= pause_button_coord[2] and pause_button_coord[1] <= y <= pause_button_coord[3]:
            if state.started and not state.paused:
                state.paused = True
                # 0000 0(cal)(reset)(start)
                # Send stop bit
                packet = bytes(5)
                print("PAUSE command sent")
                ser.write(packet)
                error_cal.get_error_stats()
        elif reset_button_coord[0] <= x <= reset_button_coord[2] and reset_button_coord[1] <= y <= reset_button_coord[3]:
            # partial reset of state variables
            state.soft_reset()
            # 0000 0(cal)(reset)(start)
            cmd = (1 << 1)
            packet = bytes([cmd]) + bytes(4)
            print("RESET command sent")
            ser.write(packet)

def get_ui_text():
    if not ser.connected:
        return ("Status: Disconnected",
                "Tap anywhere to connect")
    if ser.error:
        return ("Status: Error detected",
                "Press RESET")
    elif not ser.calibrated:
        return ("Status: Not calibrated",
                "Press CAL")
    elif ser.grip_released:
        return ("Status: Grip release",
                "Hold the grip")
    elif not ser.ready:
        return ("Status: Not ready",
                None)
    elif state.paused:
        return ("Status: Paused  -  Error stats:",
                f"MAX: {error_cal.max:.1f} RMSE: {error_cal.rmse:.1f} P95: {error_cal.p95:.1f}")
    elif state.started:
        return ("Status: Active",
                f"Error: {error:.1f}")
    else:
        return ("Status: Ready",
                None)

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
        # Convert frame to HSV for color detection
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        fps100.tick()

        # Detect marker based on color range
        mask            = cv2.inRange(frame_hsv, LOWER_GREEN, UPPER_GREEN)
        frame[mask > 0] = HIGHLIGHT # Mark all detected pixels

        # Calculate moments to find center of detected marker
        M = cv2.moments(mask)
        if M["m00"] > 0:
            state.avg_x = int(M["m10"] / M["m00"])
            state.avg_y = int(M["m01"] / M["m00"])
            frame[state.avg_y, state.avg_x] = [255, 255, 255] # Mark center
            # Convert to mm and apply offset
            mm_x, mm_y     = correct_mm(state.avg_x, state.avg_y, mtx, dist, H)
            corrected_mm_x = mm_x - state.offset_mm_x
            corrected_mm_y = mm_y - state.offset_mm_y
            if state.prev_point is not None and state.started and not state.paused:
                # Pause if there is an issue with the tool or serial connection
                if not ser.ready:
                    state.paused = True
                error, scaled_error, scaled_target_y = error_cal.get_error(state.setpoints, corrected_mm_x, corrected_mm_y)
                # Send command byte plus scaled error and target y values as 16 bit integers
                packet = struct.pack('>Bhh', (1<<0), scaled_error, scaled_target_y)
                ser.write(packet)
                # Create drawn line with color based on error magnitude
                color = set_error_color(error)
                cv2.line(state.drawn_overlay, state.prev_point, (state.avg_x, state.avg_y), color, 3)
            # Store current point for next frame's line drawing
            state.prev_point = (state.avg_x, state.avg_y)
        # Composite frame + UI
        final_screen = build_screen(frame, state.line_overlay, state.drawn_overlay, wallpaper)
        #cv2.putText(final_screen, f"{fps100.avg_fps:.1f}", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        ui_text1, ui_text2 = get_ui_text()
        # Add ui text to screen
        cv2.putText(final_screen, ui_text1, (100, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(final_screen, ui_text2, (100, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv2.imshow("Camera", final_screen)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    ser.read()

ser.close()
stream.stop()
cv2.destroyAllWindows()
