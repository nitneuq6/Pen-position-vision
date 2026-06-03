import time
import cv2
import numpy as np
import platform
import serial
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

# ── Serial Communication ────────────────────────────────────────────────────────────────────

class serial_comms:
    def __init__(self, port='/dev/ttyUSB0', baud=9600):
        self.port = port
        self.baud = baud
        self.ser = None
        self.connected = False
        self.error = False
        self.ready = False
        self.calibrated = False
        self.grip_released = False

    def start(self):
        self.close()  # ensure clean slate
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0)
            self.connected = True
            print("Serial started")
        except Exception as e:
            self.ser = None
            self.connected = False
            print(f"Serial connection failed: {e}")

    def write(self, data):
        if not self.connected:
            return
        try:
            self.ser.write(data)
        except Exception as e:
            print(f"Serial write failed: {e}")
            self.close()

    def check_incoming(self):
        if not self.connected:
            return 0
        try:
            return self.ser.in_waiting
        except Exception as e:
            print(f"Serial check failed: {e}")
            self.close()
            return 0

    def read(self):
        if not self.connected:
            return False
        try:
            if self.ser.in_waiting > 0:
                byte = self.ser.read(1)[0]
                self.error         = bool(byte & 0x01)
                self.ready         = bool(byte & 0x02)
                self.calibrated    = bool(byte & 0x04)
                self.grip_released = bool(byte & 0x08)
                return True
            return False
        except Exception as e:
            print(f"Serial read failed: {e}")
            self.close()
            return False

    def close(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.connected = False

# ── Error Tool ────────────────────────────────────────────────────────────────────

class error_tool:
    def __init__(self):
        self.error_list = []
        self.max = None
        self.mean = None

    def reset(self):
        self.error_list = []

    def get_error(self,setpoints, mm_x, mm_y):
        """Return signed error between current position and reference setpoint."""
        scaled_x = int(mm_x * 100)
        if scaled_x < 0 or scaled_x >= len(setpoints):
            return (0.0, 0, 0)
        scaled_target_y = int(setpoints[scaled_x])
        error = (scaled_target_y / 100) - mm_y
        scaled_error = int(scaled_target_y - scaled_x)
        self.error_list.append(abs(error))
        return (error, scaled_error, scaled_target_y)

    def get_max_mean(self):
        errors = np.asarray(self.error_list)
        self.max = errors.max()
        self.mean = errors.mean()
        return

# ── App State ─────────────────────────────────────────────────────────────────

class AppState:
    """Holds all mutable runtime state — eliminates global variables in main."""

    def __init__(self):
        self.running       = True
        self.started       = False
        self.paused        = False
        self.offset_x      = 0
        self.offset_y      = 100
        self.offset_mm_x   = 0.0
        self.offset_mm_y   = 0.0
        self.avg_x         = None
        self.avg_y         = None
        self.prev_point    = None
        self.line_overlay  = None
        self.drawn_overlay = np.zeros((480, 640, 3), dtype=np.uint8)
        self.menu          = True
        self.setpoints     = None
    
    def soft_reset(self):
        self.running       = True
        self.started       = False
        self.paused        = False
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

def load_selection(selection):
    """Load the pattern selected by the user from the main menu."""
    try:
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
# Program buttons
exit_button_coord  =   [725,   5,  795,  200]
start_button_coord =   [  5,   5,   75,  135]
reset_button_coord =   [  5, 275,   75,  475]
pause_button_coord =   [  5, 140,   75,  270]
imu_cal_button_coord = [725,  210, 795, 400]
# Main menu buttons
sine_button_coord =      [ 26, 272, 195, 357]
tri_button_coord =       [220, 272, 388, 357]
line_button_coord =      [412, 272, 582, 357]
terminate_button_coord = [610, 272, 780, 457]
