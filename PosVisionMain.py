from picamera2 import Picamera2
import cv2
import numpy as np
from utils import fps_counter, correct_mm, generate_line, load_selection, get_error
from utils import offset_x, offset_y, exit_button_coord, start_button_coord, avg_x, avg_y, line_overlay

# FPS counter to show performance
fps100 = fps_counter(100)
# Setpoints
setpoints = load_selection()

#### UI ####
wallpaper = cv2.imread("Main_UI.png", cv2.IMREAD_COLOR)
# UI button callback
def click_event(event, x, y, flags, param):
    global running
    global offset_x
    global offset_y
    global line_overlay
    global drawn_overlay
    global started
    global offset_mm_x
    global offset_mm_y
    if event == cv2.EVENT_LBUTTONDOWN:
        if exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
            running = False
        elif start_button_coord[0] <= x <= start_button_coord[2] and start_button_coord[1] <= y <= start_button_coord[3]:
            if avg_x is not None and avg_y is not None:
                offset_x = avg_x
                offset_y = avg_y
                offset_mm_x, offset_mm_y = correct_mm(avg_x, avg_y, mtx, dist, H)
                drawn_overlay = np.zeros((480, 640, 3), dtype=np.uint8)
                line_overlay = generate_line(offset_x, offset_y, H_inv, setpoints)
                started = True

#### CAMERA ####
# Camera settings
picam2 = Picamera2()
mode = picam2.sensor_modes[4]
config = picam2.create_preview_configuration(
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    main={'format': 'YUV420'},
    controls={"FrameDurationLimits": (1, 1)}
    )
picam2.configure(config)
width, height = picam2.camera_configuration()['main']['size']
print(f"Final Resolution: {picam2.camera_configuration()['main']['size']}")
picam2.start()
#Camera calibration
calib_data = np.load("calib_data.npz")
H = np.load("homography_matrix.npy")
H_inv = np.linalg.inv(H)
mtx = calib_data['mtx']
dist = calib_data['dist']

#### CREATE OVERLAY OF LINE ####
# Drawn overlay
drawn_overlay = np.zeros((480, 640, 3), dtype=np.uint8)
prev_point = None
#### CV SETUP ####
# Configure OpenCV window
cv2.namedWindow("Camera", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Camera", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Camera", click_event)
# Detection settings and highlight
lower_green = (35, 80, 100)
upper_green = (85, 255, 255)
highlight = [255, 0, 255]
# UI
ui_overlay = np.zeros((height, width, 3), dtype=np.uint8)
#### MAIN LOOP ####

offset_mm_x = 0
offset_mm_y = 0

running = True
started = False
while running:
    # Capture HSV frame
    frame = picam2.capture_array("main")
    frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # FPS counter
    fps100.tick()
    cv2.putText(frame, f"{fps100.avg_fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Create mask for green marker
    mask = cv2.inRange(frame_hsv, lower_green, upper_green)

    # Blur to remove noise - point detection might be worse but decent speed (50+ fps) and steady coordinates
    mask = cv2.blur(mask, (3, 3))

    # Highlight mask pixels
    frame[mask > 0] = highlight

    # Add UI
    screen = cv2.add(frame, ui_overlay)
    if line_overlay is not None:
        screen = cv2.subtract(screen, line_overlay)
    screen = cv2.subtract(screen, drawn_overlay)
    bordered_screen = cv2.copyMakeBorder(
        screen, 
        0, 0, 80, 80, 
        cv2.BORDER_CONSTANT, 
        value=[0, 0, 0] # Color to pad with (Black)
    )
    final_screen = cv2.add(wallpaper, bordered_screen)


    # Calculate coordinates of the marker
    M = cv2.moments(mask)
    if M["m00"] > 0:
        avg_x = int(M["m10"] / M["m00"])
        avg_y = int(M["m01"] / M["m00"])
        mm_x, mm_y = correct_mm(avg_x, avg_y, mtx, dist, H)
        corrected_mm_x = mm_x - offset_mm_x
        corrected_mm_y = mm_y - offset_mm_y
        #print(f"Pen is at: {avg_x}, {avg_y}, true coords: {correct_mm(avg_x, avg_y, mtx, dist, H)}")
        #print(f"uncorrected mm: {mm_x:.2f}, {mm_y:.2f}, corrected mm: {corrected_mm_x:.2f}, {corrected_mm_y:.2f}")
        if prev_point is not None and started:
            cv2.line(drawn_overlay,
                    prev_point,
                    (avg_x, avg_y),
                    (255, 255, 255),
                    1)
            error = get_error(setpoints, corrected_mm_x, corrected_mm_y)
            cv2.putText(final_screen, f"{error:.1f}", (400, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        prev_point = (avg_x, avg_y)
    cv2.imshow("Camera", final_screen)
    if cv2.waitKey(1) & 0xFF == 27:
        break

picam2.stop()
cv2.destroyAllWindows()