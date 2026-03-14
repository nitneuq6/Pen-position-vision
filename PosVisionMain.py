from picamera2 import Picamera2
import cv2
import time
import numpy as np

picam2 = Picamera2()
prev_time_frame = 0
new_time_frame = 0
width, height = 640, 480 

#0 SRGGB10_CSI2P,640x480/0 - Score: 4504.81
#1 SRGGB10_CSI2P,1640x1232/0 - Score: 1000
#2 SRGGB10_CSI2P,1920x1080/0 - Score: 1541.48
#3 SRGGB10_CSI2P,3280x2464/0 - Score: 1718
#4 SRGGB8,640x480/0 - Score: 5504.81
#5 SRGGB8,1640x1232/0 - Score: 2000
#6 SRGGB8,1920x1080/0 - Score: 2541.48
#7 SRGGB8,3280x2464/0 - Score: 2718

mode = picam2.sensor_modes[5]
config = picam2.create_preview_configuration(
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    main={'format': 'YUV420'},
    controls={"FrameDurationLimits": (5000, 5000)}
    )

picam2.configure(config)
picam2.start()

# Before loop
display_fps = 0.0
fps_text = "FPS: --"
fps_window_start = time.perf_counter()
frames_in_window = 0
fps_update_interval = 0.5  # or 1.0 for even calmer output

while True:
    frame = picam2.capture_array("main")
    #frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)     # color
    frame = frame[:height, :width]                          # grayscale
    # Count frames continuously
    frames_in_window += 1
    now = time.perf_counter()
    elapsed = now - fps_window_start

    # Update FPS text only every interval
    if elapsed >= fps_update_interval:
        display_fps = frames_in_window / elapsed
        fps_text = f"FPS: {display_fps:.0f}"
        fps_window_start = now
        frames_in_window = 0
    # Method 1
    # small blur removes noise + shadows
    #frame = cv2.GaussianBlur(frame, (3,3), 0)
    #ret, frame = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)

    # Method 2
    # estimate background lighting (very blurred)
    bg = cv2.GaussianBlur(frame, (9,9), 0)

    # normalize lighting
    norm = cv2.divide(frame, bg, scale=255)

    # detect dark lines
    _, frame = cv2.threshold(norm, 200, 255, cv2.THRESH_BINARY_INV)

    cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()

