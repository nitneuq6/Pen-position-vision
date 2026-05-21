#!/usr/bin/env python3
import cv2
import numpy as np
import subprocess
import sys

sine_button_coord = [125, 245, 290, 330]
tri_button_coord = [320, 250, 485, 330]
line_button_coord = [510, 245, 675, 330]
cal_button_coord = [205, 350, 380, 435]
exit_button_coord = [420, 350, 600, 435]

running = True

def click_event(event, x, y, flags, param):
    global running
    if event == cv2.EVENT_LBUTTONDOWN:
        if sine_button_coord[0] <= x <= sine_button_coord[2] and sine_button_coord[1] <= y <= sine_button_coord[3]:
            cv2.destroyAllWindows()
            proc = subprocess.Popen([sys.executable, "/home/user/Pen-position-vision/PosVisionMain.py"])
            proc.wait()   # waits until second script closes
            running = False
        elif tri_button_coord[0] <= x <= tri_button_coord[2] and tri_button_coord[1] <= y <= tri_button_coord[3]:
            cv2.destroyAllWindows()
            proc = subprocess.Popen([sys.executable, "/home/user/Pen-position-vision/PosVisionMain.py"])
            proc.wait()   # waits until second script closes
            running = False
        elif line_button_coord[0] <= x <= line_button_coord[2] and line_button_coord[1] <= y <= line_button_coord[3]:
            cv2.destroyAllWindows()
            proc = subprocess.Popen([sys.executable, "/home/user/Pen-position-vision/PosVisionMain.py"])
            proc.wait()   # waits until second script closes
            running = False
        elif cal_button_coord[0] <= x <= cal_button_coord[2] and cal_button_coord[1] <= y <= cal_button_coord[3]:
            cv2.destroyAllWindows()
            proc = subprocess.Popen([sys.executable, "/home/user/Pen-position-vision/PosVisionMain.py"])
            proc.wait()   # waits until second script closes
            running = False
        elif exit_button_coord[0] <= x <= exit_button_coord[2] and exit_button_coord[1] <= y <= exit_button_coord[3]:
            running = False           # stop loop

img = cv2.imread("wallpaper.png", cv2.IMREAD_COLOR)

# cv2.rectangle(img, (sine_button_coord[0], sine_button_coord[1]), (sine_button_coord[2], sine_button_coord[3]), (0, 140, 0), -1)
# cv2.rectangle(img, (exit_button_coord[0], exit_button_coord[1]), (exit_button_coord[2], exit_button_coord[3]), (0, 0, 140), -1)

cv2.namedWindow("Main Window", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Main Window", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Main Window", click_event)

while running:
    cv2.imshow("Main Window", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()