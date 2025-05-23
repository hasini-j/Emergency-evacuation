import cv2
import torch
from ultralytics import YOLO
import os

# Get absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
fire_model_path = os.path.join(current_dir, 'best.pt')
crowd_model_path = os.path.join(current_dir, 'YOLO-CROWD', 'weights', 'yolov5s.pt')

# Load models
fire_model = YOLO(fire_model_path)  # Your fire detection model
crowd_model = YOLO(crowd_model_path)  # Crowd detection model (YOLOv5)

def detect_objects(frame, model, classes=None, conf_threshold=0.5):
    """Run inference and return detected objects above confidence threshold"""
    results = model(frame, verbose=False)[0]  # Disable logging
    detections = []
    for box, cls, conf in zip(results.boxes.xyxy, results.boxes.cls, results.boxes.conf):
        if (classes is None or int(cls) in classes) and conf >= conf_threshold:
            detections.append({
                'box': box.tolist(),
                'class': int(cls),
                'confidence': float(conf)
            })
    return detections

# Camera setup
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Fire detection with threshold
    fire_detections = detect_objects(frame, fire_model, conf_threshold=0.5)
    
    # Crowd detection (class 0 = person) with threshold
    crowd_detections = detect_objects(frame, crowd_model, classes=[0], conf_threshold=0.75)
    person_count = len(crowd_detections)

    # Draw fire detections (red boxes)
    for det in fire_detections:
        x1, y1, x2, y2 = map(int, det['box'])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(frame, f'Fire {det["confidence"]:.2f}',
                   (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Draw crowd detections (green boxes)
    for det in crowd_detections:
        x1, y1, x2, y2 = map(int, det['box'])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Display counts
    cv2.putText(frame, f'People: {person_count}', (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, f'Fires: {len(fire_detections)}', (10, 70),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow('Fire & Crowd Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
