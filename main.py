import cv2
from PIL import Image
from util import get_limits

yellow = [0,255,255] # this is yellow in BGR colourspace
cap = cv2.VideoCapture(0) 

while True:
    ret, frame = cap.read() # read gives boolean if frame was grabbed & NumPy array (rows x columns x color channels)

    hsvImage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lowerLimit, upperLimit = get_limits(color=yellow)
    mask = cv2.inRange(hsvImage, lowerLimit, upperLimit) # this mask shows white for objects with those colours, black if not

    mask_ = Image.fromarray(mask) # converting image from num py array to pillow

    bbox = mask_.getbbox() # boundary box

    if bbox is not None:
        x1, y1, x2, y2 = bbox

        cv2.rectangle(frame, (x1, y1), (x2, y2), (203, 192, 255), 7)

    cv2.imshow('frame', frame) # displays current frame

    # waits for 1 ms for a keyboad input, returns a number for whatever key it was pressed for, -1 if none
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

cap.release() # releases the camera so other programs can use it

cv2.destroyAllWindows() # closes all openCV windows that were opened


