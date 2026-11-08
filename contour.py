import cv2
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
MIN_AREA = 500

cap = cv2.VideoCapture(0) 

while True:
    ret, frame = cap.read() # read gives boolean if frame was grabbed & NumPy array (rows x columns x color channels)
    hsvImage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    for name, props in colors.items():
        lowerLimit, upperLimit = get_limits(color=props['bgr'])
        mask = cv2.inRange(hsvImage, lowerLimit, upperLimit) # this mask shows white for objects with those colours, black if not
        
        # external is only outer boundaries, chain approx simple is to compress contour points to save memory
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        found = False

        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > MIN_AREA:
                found = True
                x, y, w, h = cv2.boundingRect(largest)
                cv2.rectangle(frame, (x, y), (x + w, y + h), props['box_color'], 3)
                cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, props['box_color'], 2)

                # calculating centroid
                cx, cy = x + w // 2, y + h // 2
                cv2.circle(frame, (cx, cy), 5, props['box_color'], -1)

                # add newest point to front
                trails[name].appendleft((cx,cy))
        if not found:
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