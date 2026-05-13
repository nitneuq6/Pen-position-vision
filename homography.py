from picamera2 import Picamera2
import numpy as np
import cv2 as cv

# Settings
board_size = (7, 5) # Internal corners
square_size = 20 # Square size in mm

# Load calibration data
data = np.load("calib_data.npz")
mtx = data["mtx"]
dist = data["dist"]

# Camera setup
picam2 = Picamera2()
mode = picam2.sensor_modes[4]

config = picam2.create_preview_configuration(
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    main={'format': 'YUV420'},
    controls={"FrameDurationLimits": (1, 1)}
)

picam2.configure(config)
picam2.start()

# Prepare object points based on board size and square size
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
objp *= square_size

print("Place board flat.")
print("Press SPACE to capture.")

while True:
    frame_yuv = picam2.capture_array("main")
    img = cv.cvtColor(frame_yuv, cv.COLOR_YUV420p2RGB)

    undistorted = cv.undistort(img, mtx, dist)

    gray = cv.cvtColor(undistorted, cv.COLOR_BGR2GRAY)

    ret, corners = cv.findChessboardCorners(gray, board_size, None)

    display = undistorted.copy()

    if ret:
        corners2 = cv.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
        cv.drawChessboardCorners(display, board_size, corners2, ret)

    cv.imshow("Homography", display)

    key = cv.waitKey(1) & 0xFF

    if key == 32:
        if ret:
            H, _ = cv.findHomography(corners2, objp[:, :2])

            np.save("homography_matrix.npy", H)

            print("homography_matrix.npy saved")
            print(H)

            break
        else:
            print("Board not detected")

    elif key == 27:
        break

picam2.stop()
cv.destroyAllWindows()