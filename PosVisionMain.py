#
#   This is the main file for the FinMo vision system.
#   Test change2
from picamera2 import Picamera2
import cv2

# Initialize camera
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (3280, 2464), "format": "RGB888"},
    lores={"size": (1280, 720), "format": "YUV420"},
    controls={"FrameDurationLimits": (33333, 33333)},
)
picam2.configure(config)
picam2.start()

# Capture loop
while True:
    # Use lores stream for faster preview; full-resolution stream remains configured in "main"
    frame = picam2.capture_array("lores")
    preview = cv2.cvtColor(frame, cv2.COLOR_YUV2RGB_I420)  # Convert YUV to RGB for display
    cv2.imshow("Camera", preview)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break

cv2.destroyAllWindows()