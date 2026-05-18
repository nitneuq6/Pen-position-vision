#!/usr/bin/env python3
import cv2
import numpy as np
import subprocess
import sys

start_button_coord = [50, 50, 160, 100]
exit_button_coord = [50, 150, 160, 200]

running = True

def click_event(event, x, y, flags, param):
    global running
    if event == cv2.EVENT_LBUTTONDOWN:
        if start_button_coord[0] <= x <= start_button_coord[2] and start_button_coord[1] <= y <= start_button_coord[3]:
            cv2.destroyAllWindows()
            proc = subprocess.Popen([sys.executable, "/home/user/Pen-position-vision/PosVisionMain.py"])
            proc.wait()   # waits until second script closes
            running = False

        elif exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
            running = False           # stop loop

img = np.zeros((480, 800, 3), dtype=np.uint8)

cv2.rectangle(img, (start_button_coord[0], start_button_coord[1]), (start_button_coord[2], start_button_coord[3]), (0, 140, 0), -1)
cv2.putText(img, "RUN", (65, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
cv2.rectangle(img, (exit_button_coord[0], exit_button_coord[1]), (exit_button_coord[2], exit_button_coord[3]), (0, 0, 140), -1)
cv2.putText(img, "EXIT", (65, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

cv2.namedWindow("Main Window", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Main Window", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Main Window", click_event)

while running:
    cv2.imshow("Main Window", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()