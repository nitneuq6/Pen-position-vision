import time
import cv2
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

# Load selected pattern
def load_selection():
    try:
        with open("selection.txt", "r") as f:
            selection = f.read().strip()
        if selection == "sine":
            return np.load("sine.npy")
        elif selection == "triangle":
            return np.load("triangle.npy")
        elif selection == "line":
            return np.zeros((100, 2))
        else:
            return None
    except FileNotFoundError:
        return None

# Convert pixel to mm using camera calibration data and homography
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

# Generate reference line
def generate_line(offset_x, offset_y, H_inv, setpoints):
    #Load selected pattern as setpoints
    setpoint_data = setpoints
    # Create image
    line_overlay = np.zeros((480, 640, 3), dtype=np.uint8)

    # Scale points
    scale = 92 / 9200

    points = np.array([
        [x * scale, y * scale, 0]
        for x, y in enumerate(setpoint_data)
    ], dtype=np.float32)


    # Draw
    for p in points:
        px_raw, py_raw, _ = p
        
        # Pack the point into the required format (1, 1, 2)
        pt_mm = np.array([[[px_raw, py_raw]]], dtype=np.float32)
        
        # Transform directly using the inverse homography
        pt_pixel = cv2.perspectiveTransform(pt_mm, H_inv) 
        px = int(round(pt_pixel[0, 0, 0])) + offset_x - 165
        py = int(round(pt_pixel[0, 0, 1])) + offset_y - 105
        
        # Draw directly
        if 0 <= px < line_overlay.shape[1] and 0 <= py < line_overlay.shape[0]:
            line_overlay[py, px] = (255, 255, 255)
    return line_overlay

def get_error(setpoints, mm_x, mm_y):
    scaled_x = int(mm_x * 100)
    if scaled_x < 0 or scaled_x >= len(setpoints):
        return 0
    else:
        target_y = setpoints[scaled_x] / 100
        error = target_y - mm_y
        return error



_point_buffer = np.zeros((1, 1, 2), dtype=np.float32)
offset_x = 0
offset_y = 100

exit_button_coord = [725, 5, 795, 200]
start_button_coord = [5, 5, 75, 135]
avg_x = None
avg_y = None
line_overlay = None  