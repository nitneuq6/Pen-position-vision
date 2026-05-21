from picamera2 import Picamera2
import cv2
import time
import numpy as np

class fps_counter:
    def __init__(self, frame_count_top):
        self.start_time = 0
        self.frame_count = frame_count_top
        self.frame_count_top = frame_count_top
        self.avg_fps = 0
    def tick(self):
        self.frame_count += 1
        if(self.frame_count >= self.frame_count_top):
            self.calc_fps()
            self.frame_count = 0
            self.start()
    def start(self):
        self.start_time = time.perf_counter()
    def calc_fps(self):
        end_time = time.perf_counter()
        elapsed_time = end_time - self.start_time
        fps = self.frame_count / elapsed_time
        self.avg_fps = fps

def load_selection():
    try:
        with open("selection.txt", "r") as f:
            selection = f.read().strip()
        if selection is "sine":
            return np.load("sine.npy")
        elif selection is "triangle":
            return np.load("triangle.npy")
        elif selection is "line":
            return np.zeros((100, 2))
        else:
            return None
    except FileNotFoundError:
        return None

def click_event(event, x, y, flags, param):
    global running
    if event == cv2.EVENT_LBUTTONDOWN:
        if exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
            running = False

_point_buffer = np.zeros((1, 1, 2), dtype=np.float32)
def correct_mm(x, y, mtx, dist, H):
    global _point_buffer
    # Update the existing buffer instead of creating a new one
    _point_buffer[0, 0, 0] = float(x)
    _point_buffer[0, 0, 1] = float(y)
    # 1. Undistort the point
    undistorted = cv2.undistortPoints(_point_buffer, mtx, dist, P=mtx)
    # 2. Apply Homography to move from Pixels -> Millimeters
    mm_point = cv2.perspectiveTransform(undistorted, H)
    # Return as a simple tuple
    return round(float(mm_point[0, 0, 0] + offset_x), 2), round(float(mm_point[0, 0, 1] + offset_y), 2)

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
mtx = calib_data['mtx']
dist = calib_data['dist']

offset_x = 32
offset_y = 28

# FPS counter setup
fps100 = fps_counter(100)
triple_thres = (120, 150)

# Load selected pattern as setpoints
setpoint_data = load_selection()

# Configure OpenCV window
cv2.namedWindow("Camera", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Camera", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Camera", click_event)
# UI
exit_button_coord = [50, 50, 200, 100]
ui_overlay = np.zeros((height, width, 3), dtype=np.uint8)

cv2.rectangle(ui_overlay,
              (exit_button_coord[0], exit_button_coord[1]),
              (exit_button_coord[2], exit_button_coord[3]),
              (255, 0, 0), -1)

cv2.putText(ui_overlay,
            "EXIT",
            (65, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2)


# Detection loop
running = True
while running:
    # Capture HSV frame
    frame = picam2.capture_array("main")
    frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

    # FPS counter
    fps100.tick()
    cv2.putText(frame, f"{fps100.avg_fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Create mask for green marker
    lower_green = (35, 80, 80)
    upper_green = (85, 255, 255)
    mask = cv2.inRange(frame_hsv, lower_green, upper_green)
    highlight = [255, 0, 255]

    # Blur to remove noise - point detection might be worse but decent speed (50+ fps) and steady coordinates
    mask = cv2.medianBlur(mask, 3)

    # Highlight mask pixels
    frame[mask > 0] = highlight
    # Add UI
    screen = cv2.add(frame, ui_overlay)
    cv2.imshow("Camera", screen)
    #cv2.imshow("Detection Mask", mask)

    # Calculate coordinates of the marker
    coords = np.column_stack(np.where(mask > 0))
    if coords.size > 0:
        # Calculate the average Y and X (NumPy uses Row, Col order)
        avg_y, avg_x = np.mean(coords, axis=0).astype(int)
        
        # Now you have the (avg_x, avg_y) center point!
        print(f"Pen is at: {avg_x}, {avg_y}, true coords: {correct_mm(avg_x, avg_y, mtx, dist, H)}")

    if cv2.waitKey(1) & 0xFF == 27:
        break

picam2.stop()
cv2.destroyAllWindows()






#0 SRGGB10_CSI2P,640x480/0 - Score: 4504.81
#1 SRGGB10_CSI2P,1640x1232/0 - Score: 1000
#2 SRGGB10_CSI2P,1920x1080/0 - Score: 1541.48
#3 SRGGB10_CSI2P,3280x2464/0 - Score: 1718
#4 SRGGB8,640x480/0 - Score: 5504.81
#5 SRGGB8,1640x1232/0 - Score: 2000
#6 SRGGB8,1920x1080/0 - Score: 2541.48
#7 SRGGB8,3280x2464/0 - Score: 2718



    # Method 1
    # small blur removes noise + shadows
    #frame = cv2.GaussianBlur(frame, (3,3), 0)
    #ret, frame = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)

    # Method 2
    # estimate background lighting (very blurred)
    #bg = cv2.GaussianBlur(frame, (9,9), 0)

    # normalize lighting
    #norm = cv2.divide(frame, bg, scale=255)

    # detect dark lines
    #_, frame = cv2.threshold(frame, 120, 255, cv2.THRESH_BINARY_INV)
    # result = np.zeros_like(frame)
    # result[frame < triple_thres[0]] = 0
    # result[(frame >= triple_thres[0]) & (frame < triple_thres[1])] = 100
    # result[frame >= triple_thres[1]] = 255

    #edges = cv2.Canny(frame, 50, 150)
    #lines = cv2.HoughLinesP(edges, 1, 3.14/180, 50)

    # Opening to remove noise -> poor detection for small points 50+ fps
    # kernel = np.ones((3, 3), np.uint8)
    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Gaus -> nice point and performance but unsteady coordinates
    #mask = cv2.GaussianBlur(mask, (3,3), 0)

    # Only keep large groups -> possibly best point detection, 40-50 fps
    # num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    # mask = np.zeros(mask.shape, dtype="uint8")
    # for i in range(1, num_labels):
    #     area = stats[i, cv2.CC_STAT_AREA]
    #     if area > 5:
    #         mask[labels == i] = 255
