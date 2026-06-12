import numpy as np
import cv2
import platform
from utils import WinCameraStream, CameraStream

if platform.system() == "Linux":
    stream         = CameraStream()
else:
    stream         = WinCameraStream()


width, height  = stream.width, stream.height
center_x, center_y = int(width // 2), int(height // 2)



exit_button_clicked = False
exit_button_coord = [10, 10, 110, 60]
def click_event(event, x, y, flags, param):
    global exit_button_clicked
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
        exit_button_clicked = True

cv2.namedWindow("Homography", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Homography", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Homography", click_event)

while True:
    frame     = stream.read()
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    frame[center_y, center_x] = [255, 255, 255]
    cv2.circle(frame, (center_x, center_y), 5, (255, 255, 255), 1)
    hsv_value = frame_hsv[center_y, center_x]



    cv2.rectangle(frame, (exit_button_coord[0], exit_button_coord[1]), (exit_button_coord[2], exit_button_coord[3]), (0, 0, 140), -1)
    cv2.putText(frame, "EXIT", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, f"HSV: {hsv_value}", (180, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow("Homography", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == 27 or exit_button_clicked:  # ESC or click
        break

stream.stop()
cv2.destroyAllWindows()