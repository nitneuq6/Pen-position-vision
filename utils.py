import time
import cv2
import numpy as np
import platform
if platform.system() == "Linux":
    from picamera2 import Picamera2

# ── Camera ────────────────────────────────────────────────────────────────────

class CameraStream:
    """Simple PiCamera2 wrapper — no threading, direct capture each frame."""

    def __init__(self):
        self.picam2 = Picamera2()
        mode = self.picam2.sensor_modes[4]
        config = self.picam2.create_preview_configuration(
            sensor={"output_size": mode["size"], "bit_depth": mode["bit_depth"]},
            main={"format": "RGB888"},
            controls={"FrameDurationLimits": (1, 1)},
        )
        self.picam2.configure(config)
        self.width, self.height = self.picam2.camera_configuration()["main"]["size"]
        self.picam2.start()

    def read(self):
        return self.picam2.capture_array("main")

    def stop(self):
        self.picam2.stop()

class WinCameraStream:
    def __init__(self):
        self.cam = cv2.VideoCapture(0)
        self.width = int(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def read(self):
        ret, frame = self.cam.read()
        return frame if ret else None

    def stop(self):
        self.cam.release()

# ── App State ─────────────────────────────────────────────────────────────────

class AppState:
    """Holds all mutable runtime state — eliminates global variables in main."""

    def __init__(self):
        self.running       = True
        self.started       = False
        self.offset_x      = 0
        self.offset_y      = 100
        self.offset_mm_x   = 0.0
        self.offset_mm_y   = 0.0
        self.avg_x         = None
        self.avg_y         = None
        self.prev_point    = None
        self.line_overlay  = None
        self.drawn_overlay = np.zeros((480, 640, 3), dtype=np.uint8)


# ── FPS Counter ───────────────────────────────────────────────────────────────

class fps_counter:
    def __init__(self, frame_count_top):
        self.frame_count_top = frame_count_top
        self.frame_count     = frame_count_top
        self.start_time      = 0.0
        self.avg_fps         = 0.0

    def tick(self):
        self.frame_count += 1
        if self.frame_count >= self.frame_count_top:
            self._calc_fps()
            self.frame_count = 0
            self.start_time  = time.perf_counter()

    def _calc_fps(self):
        elapsed      = time.perf_counter() - self.start_time
        self.avg_fps = self.frame_count / elapsed if elapsed > 0 else 0.0


# ── Screen Compositing ────────────────────────────────────────────────────────

def build_screen(frame, line_overlay, drawn_overlay, wallpaper):
    """Composite camera frame with all overlays and wallpaper border."""
    if line_overlay is not None:
        frame = cv2.subtract(frame, line_overlay)
    screen = cv2.subtract(frame, drawn_overlay)
    wallpaper[:, 80:720] = screen
    return wallpaper


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_selection():
    """Load the pattern selected by the user from selection.txt."""
    try:
        with open("selection.txt", "r") as f:
            selection = f.read().strip()
        patterns = {
            "sine":     "sine.npy",
            "triangle": "triangle.npy",
        }
        if selection in patterns:
            return np.load(patterns[selection])
        elif selection == "line":
            return np.zeros(9200)
    except FileNotFoundError:
        pass
    return None


def correct_mm(x, y, mtx, dist, H):
    """Convert pixel coordinates to mm using calibration data and homography."""
    _point_buffer[0, 0, 0] = float(x)
    _point_buffer[0, 0, 1] = float(y)
    undistorted = cv2.undistortPoints(_point_buffer, mtx, dist, P=mtx)
    mm_point    = cv2.perspectiveTransform(undistorted, H)
    return (
        round(float(mm_point[0, 0, 0]) + offset_x, 2),
        round(float(mm_point[0, 0, 1]) + offset_y, 2),
    )


def generate_line(offset_x, offset_y, H_inv, setpoints):
    """Generate a pixel-space overlay of the reference line from mm setpoints."""
    line_overlay = np.zeros((480, 640, 3), dtype=np.uint8)
    scale = 92 / 9200

    for i, sp in enumerate(setpoints):
        pt_mm  = np.array([[[i * scale, sp * scale]]], dtype=np.float32)
        pt_px  = cv2.perspectiveTransform(pt_mm, H_inv)
        px = int(round(pt_px[0, 0, 0])) + offset_x - 165
        py = int(round(pt_px[0, 0, 1])) + offset_y - 105
        if 0 <= px < line_overlay.shape[1] and 0 <= py < line_overlay.shape[0]:
            line_overlay[py, px] = (255, 255, 255)

    return line_overlay


def get_error(setpoints, mm_x, mm_y):
    """Return signed error between current position and reference setpoint."""
    scaled_x = int(mm_x * 100)
    if scaled_x < 0 or scaled_x >= len(setpoints):
        return 0.0
    return setpoints[scaled_x] / 100 - mm_y

def set_error_color(error):
    """Return a color based on the magnitude of the error."""
    error = abs(error)
    if error <= 1:
        green = 80
        red = 255
    else:
        red = 0
        green = 255

    return (255, green, red)  

# ── Module-level constants ────────────────────────────────────────────────────

_point_buffer = np.zeros((1, 1, 2), dtype=np.float32)

offset_x = 0
offset_y = 100

exit_button_coord  = [725,   5, 795, 200]
start_button_coord = [  5,   5,  75, 135]
