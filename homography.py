import numpy as np
import cv2
import platform
from utils import WinCameraStream, CameraStream

if platform.system() == "Linux":
    stream         = CameraStream()
else:
    stream         = WinCameraStream()

# Settings
board_size = (7, 5) # Internal corners
square_size = 19 # Square size in mm

# Load calibration data
data = np.load("calib_data.npz")
mtx = data["mtx"]
dist = data["dist"]

# Prepare object points based on board size and square size
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
objp *= square_size

print("Place board flat.")
print("Press SPACE to capture.")

cal_button_clicked = False
exit_button_clicked = False
cal_button_coord = [50, 50, 200, 100]
exit_button_coord = [50, 150, 200, 200]
def click_event(event, x, y, flags, param):
    global cal_button_clicked
    global exit_button_clicked
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if cal_button_coord[0] <= x <= cal_button_coord[2] and cal_button_coord[1] <= y <= cal_button_coord[3]:
        cal_button_clicked = True
    elif exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
        exit_button_clicked = True

cv2.namedWindow("Homography", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Homography", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Homography", click_event)

while True:
    img     = stream.read()

    undistorted = cv2.undistort(img, mtx, dist)

    gray = cv2.cvtColor(undistorted, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, board_size, None)

    display = undistorted.copy()

    if ret:
        corners2 = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
        cv2.drawChessboardCorners(display, board_size, corners2, ret)
    cv2.rectangle(display, (cal_button_coord[0], cal_button_coord[1]), (cal_button_coord[2], cal_button_coord[3]), (0, 140, 0), -1)
    cv2.putText(display, "CALIBRATE", (65, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.rectangle(display, (exit_button_coord[0], exit_button_coord[1]), (exit_button_coord[2], exit_button_coord[3]), (0, 0, 140), -1)
    cv2.putText(display, "EXIT", (65, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow("Homography", display)

    key = cv2.waitKey(1) & 0xFF

    if key == 32 or cal_button_clicked:  # SPACE or click
        cal_button_clicked = False
        if ret:
            H, _ = cv2.findHomography(corners2, objp[:, :2])

            np.save("homography_matrix.npy", H)

            print("homography_matrix.npy saved")
            print(H)

            break
        else:
            print("Board not detected")

    elif key == 27 or exit_button_clicked:  # ESC or click
        break

stream.stop()
cv2.destroyAllWindows()