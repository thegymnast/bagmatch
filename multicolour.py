import cv2
from PIL import Image
from collections import deque
from util import get_limits

# defining colours in BGR
colors = {
    'yellow': {'bgr': [0,255,255], 'box_color': (0, 255, 255)},
    'blue': {'bgr': [255,0,0], 'box_color': (255,0,0)},
    'green': {'bgr': [0,255,0], 'box_color': (0,255,0)},
}

# one trail per colour, storing max 32 points
trails = {name: deque(maxlen=32) for name in colors}

cap = cv2.VideoCapture(0) 

while True:
    ret, frame = cap.read() # read gives boolean if frame was grabbed & NumPy array (rows x columns x color channels)
    hsvImage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    for name, props in colors.items():
        lowerLimit, upperLimit = get_limits(color=props['bgr'])
        mask = cv2.inRange(hsvImage, lowerLimit, upperLimit) # this mask shows white for objects with those colours, black if not
        mask_ = Image.fromarray(mask) # converting image from num py array to pillow
        bbox = mask_.getbbox() # boundary box

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), props['box_color'], 7)
            cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, props['box_color'], 2)

            # calculating cnetroid
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            cv2.circle(frame, (cx, cy), 5, props['box_color'], -1)

            # add newest point to front
            trails[name].appendleft((cx,cy))
        else:
            trails[name].appendleft(None)
    
        pts = trails[name]
        for i in range(1, len(pts)):
            if pts[i - 1] is None or pts[i] is None:
                continue
            thickness = int(3 * (1 - i / len(pts))) + 1
            cv2.line(frame, pts[i - 1], pts[i], props['box_color'], thickness)
    cv2.imshow('frame', frame) # displays current frame

    # waits for 1 ms for a keyboad input, returns a number for whatever key it was pressed for, -1 if none
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

cap.release() # releases the camera so other programs can use it

cv2.destroyAllWindows() # closes all openCV windows that were opened