from picamera2 import Picamera2
import cv2
import time
import numpy as np
import glob

class fps_counter:
    def __init__(self, frame_count_top):
        self.start_time = 0
        self.frame_count = frame_count_top
        self.frame_count_top = frame_count_top
        self.avg_fps = 0
    def tick(self):
        self.frame_count += 1
        if(self.frame_count >= self.frame_count_top):
            self.calc_fps()
            self.frame_count = 0
            self.start()
    def start(self):
        self.start_time = time.perf_counter()
    def calc_fps(self):
        end_time = time.perf_counter()
        elapsed_time = end_time - self.start_time
        fps = self.frame_count / elapsed_time
        self.avg_fps = fps



picam2 = Picamera2()

#0 SRGGB10_CSI2P,640x480/0 - Score: 4504.81
#1 SRGGB10_CSI2P,1640x1232/0 - Score: 1000
#2 SRGGB10_CSI2P,1920x1080/0 - Score: 1541.48
#3 SRGGB10_CSI2P,3280x2464/0 - Score: 1718
#4 SRGGB8,640x480/0 - Score: 5504.81
#5 SRGGB8,1640x1232/0 - Score: 2000
#6 SRGGB8,1920x1080/0 - Score: 2541.48
#7 SRGGB8,3280x2464/0 - Score: 2718

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

# Before loop
fps100 = fps_counter(100)
triple_thres = (120, 150)

while True:
    frame = picam2.capture_array("main")
    frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)     # color
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    #frame = frame[:height, :width]                          # grayscale

    # Method 1
    # small blur removes noise + shadows
    #frame = cv2.GaussianBlur(frame, (3,3), 0)
    #ret, frame = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)

    # Method 2
    # estimate background lighting (very blurred)
    #bg = cv2.GaussianBlur(frame, (9,9), 0)

    # normalize lighting
    #norm = cv2.divide(frame, bg, scale=255)

    # detect dark lines
    #_, frame = cv2.threshold(frame, 120, 255, cv2.THRESH_BINARY_INV)
    # result = np.zeros_like(frame)
    # result[frame < triple_thres[0]] = 0
    # result[(frame >= triple_thres[0]) & (frame < triple_thres[1])] = 100
    # result[frame >= triple_thres[1]] = 255

    #edges = cv2.Canny(frame, 50, 150)
    #lines = cv2.HoughLinesP(edges, 1, 3.14/180, 50)

    fps100.tick()
    cv2.putText(frame, f"{fps100.avg_fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)


    lower_green = (35, 80, 80)
    upper_green = (85, 255, 255)
    
    mask = cv2.inRange(frame_hsv, lower_green, upper_green)
    highlight = [255, 0, 255]

    # Opening to remove noise -> poor detection for small points 50+ fps
    # kernel = np.ones((3, 3), np.uint8)
    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Blur to remove noise - point detection might be worse but decent speed (50+ fps) and steady coordinates
    mask = cv2.medianBlur(mask, 3)

    # Gaus -> nice point and performance but unsteady coordinates
    #mask = cv2.GaussianBlur(mask, (3,3), 0)

    # Only keep large groups -> possibly best point detection, 40-50 fps
    # num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    # mask = np.zeros(mask.shape, dtype="uint8")
    # for i in range(1, num_labels):
    #     area = stats[i, cv2.CC_STAT_AREA]
    #     if area > 5:
    #         mask[labels == i] = 255

    # Highlight mask pixels
    frame[mask > 0] = highlight

    cv2.imshow("Camera", frame)
    #cv2.imshow("Detection Mask", mask)

    coords = np.column_stack(np.where(mask > 0))
    if coords.size > 0:
        # Calculate the average Y and X (NumPy uses Row, Col order)
        avg_y, avg_x = np.mean(coords, axis=0).astype(int)
        
        # Now you have the (avg_x, avg_y) center point!
        print(f"Pen is at: {avg_x}, {avg_y}")

    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()

