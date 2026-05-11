from picamera2 import Picamera2
import numpy as np
import cv2 as cv



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

# 1. Setup criteria and object points (for a 7x6 internal corner board)
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
board_size = (7, 5) # Internal corners

objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
objp[:,:2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1,2)

objpoints = [] 
imgpoints = [] 

# 2. Capture from PiCam2 (Assuming your picam2 setup is above this)
print("Capturing calibration frame...")
frame_yuv = picam2.capture_array("main")
img = cv.cvtColor(frame_yuv, cv.COLOR_YUV420p2RGB)     # color
gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

# while True:
#     cv.imshow("Camera", gray)
#     if cv.waitKey(1) & 0xFF == 27:
#         break

# 3. Find the corners
ret, corners = cv.findChessboardCorners(gray, board_size, None)

if ret:
    objpoints.append(objp)
    corners2 = cv.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
    imgpoints.append(corners2)

    # Draw result
    cv.drawChessboardCorners(img, board_size, corners2, ret)
    cv.imshow('Calibration Result', img)
    print("Board found! Press any key to calculate calibration...")
    cv.waitKey(0)

    # 4. Final Calibration Calculation
    # This generates the matrices you need for your 'fix_point' logic
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    # Save the matrices so you can load them in your tracking script
    np.savez("calib_data.npz", mtx=mtx, dist=dist)
    print("Calibration saved to calib_data.npz")

else:
    print("Chessboard not found. Try adjusting the light or distance.")

cv.destroyAllWindows()