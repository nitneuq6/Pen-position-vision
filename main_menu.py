import cv2
import numpy as np
import subprocess
import sys

button_coord = [50, 50, 160, 100]
button2_coord = [50, 150, 160, 200]

running = True

def click_event(event, x, y, flags, param):
    global running
    if event == cv2.EVENT_LBUTTONDOWN:
        if button_coord[0] <= x <= button_coord[2] and button_coord[1] <= y <= button_coord[3]:
            print("Canvas Button Clicked!")
            cv2.destroyAllWindows()
            proc = subprocess.Popen([sys.executable, "test.py"])
            proc.wait()   # waits until second script closes
            running = False

        elif button2_coord[0] <= x <= button2_coord[2] and button2_coord[1] <= y <= button2_coord[3]:
            print("Canvas Button 2 Clicked!")
            running = False           # stop loop

img = np.zeros((300, 400, 3), dtype=np.uint8)

cv2.rectangle(img, (button_coord[0], button_coord[1]), (button_coord[2], button_coord[3]), (0, 140, 0), -1)
cv2.putText(img, "RUN", (65, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
cv2.rectangle(img, (button2_coord[0], button2_coord[1]), (button2_coord[2], button2_coord[3]), (0, 0, 140), -1)
cv2.putText(img, "EXIT", (65, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

cv2.namedWindow("Main Window", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Main Window", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("Main Window", click_event)

while running:
    cv2.imshow("Main Window", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()