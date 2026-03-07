#
#   This is the main file for the FinMo vision system.
#   Test change2
from picamera2 import Picamera2
import cv2

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

# Capture loop
while True:
    frame = picam2.capture_array()  # NumPy array directly usable in OpenCV
    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break

cv2.destroyAllWindows()