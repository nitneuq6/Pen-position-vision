from picamera2 import Picamera2
import cv2
import time

picam2 = Picamera2()
prev_time_frame = 0
new_time_frame = 0
width, height = 640, 480 

# SRGGB10_CSI2P,640x480/0 - Score: 4504.81
# SRGGB10_CSI2P,1640x1232/0 - Score: 1000
# SRGGB10_CSI2P,1920x1080/0 - Score: 1541.48
# SRGGB10_CSI2P,3280x2464/0 - Score: 1718
# SRGGB8,640x480/0 - Score: 5504.81
# SRGGB8,1640x1232/0 - Score: 2000
# SRGGB8,1920x1080/0 - Score: 2541.48
# SRGGB8,3280x2464/0 - Score: 2718

# config = picam2.create_preview_configuration(
#     main={"size": (width, height), "format": "YUV420"},
#     buffer_count=6,
#     controls={"FrameDurationLimits": (1, 5000)},
# )
mode = picam2.sensor_modes[4]
config = picam2.create_preview_configuration(
    sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
    controls={"FrameDurationLimits": (1, 5000)}
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
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    # gray = frame[:height, :] 
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

    cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()

