from picamera2 import Picamera2
import numpy as np
import cv2 as cv

# Settings
board_size = (8, 5) # Internal corners of the chessboard pattern used for calibration
square_size = 15 # Size of each square in mm
num_required = 20 # Number of calibration images to capture

# Camera setup
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

cal_button_clicked = False
exit_button_clicked = False
cal_button_coord = [50, 50, 200, 100]
exit_button_coord = [50, 150, 200, 200]
def click_event(event, x, y, flags, param):
    global cal_button_clicked
    global exit_button_clicked
    if event != cv.EVENT_LBUTTONDOWN:
        return
    if cal_button_coord[0] <= x <= cal_button_coord[2] and cal_button_coord[1] <= y <= cal_button_coord[3]:
        cal_button_clicked = True
    elif exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
        exit_button_clicked = True

# 1. Setup criteria and object points
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
objp *= square_size

objpoints = []
imgpoints = []

captured = 0

print("Press SPACE to capture board.")
print("Move board each time (tilt/rotate/shift).")
print("Press ESC when done.")

cv.namedWindow("Calibration", cv.WND_PROP_FULLSCREEN)
cv.setWindowProperty("Calibration", cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)
cv.setMouseCallback("Calibration", click_event)

# 2. Capture from PiCam2
print("Capturing calibration frame.")
while True:
    frame_yuv = picam2.capture_array("main")
    img = cv.cvtColor(frame_yuv, cv.COLOR_YUV420p2RGB)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    display = img.copy()
    ret, corners = cv.findChessboardCorners(gray, board_size, None)

    if ret:
        corners2 = cv.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
        cv.drawChessboardCorners(display, board_size, corners2, ret)

    cv.putText(display, f"Captured: {captured}/{num_required}",
               (20, 40), cv.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv.rectangle(display, (cal_button_coord[0], cal_button_coord[1]), (cal_button_coord[2], cal_button_coord[3]), (0, 140, 0), -1)
    cv.putText(display, "CALIBRATE", (65, 80), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv.rectangle(display, (exit_button_coord[0], exit_button_coord[1]), (exit_button_coord[2], exit_button_coord[3]), (0, 0, 140), -1)
    cv.putText(display, "EXIT", (65, 180), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv.imshow("Calibration", display)

    key = cv.waitKey(1) & 0xFF

    if key == 32 or cal_button_clicked:  # SPACE
        cal_button_clicked = False
        if ret:
            objpoints.append(objp)
            imgpoints.append(corners2)
            captured += 1
            print(f"Captured {captured}/{num_required}")
        else:
            print("Chessboard not detected")

    elif key == 27 or exit_button_clicked:  # ESC
        break

    if captured >= num_required:
        break

# Calibrate camera if enough images were captured
if len(objpoints) >= 5:
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None
    )

    np.savez("calib_data.npz", mtx=mtx, dist=dist)

    print("\nCalibration saved:")
    print("calib_data.npz")
    print("\nCamera matrix:")
    print(mtx)

else:
    print("Not enough images.")

picam2.stop()
cv.destroyAllWindows()