from picamera2 import Picamera2
import cv2

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"size": (1920, 1080)},
    lores={"size": (960, 540), "format": "YUV420"},
    controls={"FrameDurationLimits": (16667, 16667)}
)

picam2.configure(config)
picam2.start()

while True:
    frame = picam2.capture_array("lores")

    # Convert YUV420 -> BGR for OpenCV
    frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()