import cv2
import torch
import numpy as np
from ultralytics import YOLO
import yaml
from pathlib import Path

# 1. 创建增强版临时配置文件，明确“hand”语义
target_class = "hand"
classes = [f"{target_class} (only human hand, no arm/body)"]
config = {
    "names": {i: cls for i, cls in enumerate(classes)},
    "nc": len(classes),
    "train": "",
    "val": "",
    "test": ""
}
config_path = Path("temp_hand_config.yaml")
with open(config_path, "w") as f:
    yaml.dump(config, f)

# 2. 加载模型并覆盖类别映射
model = YOLO("yolov8s-worldv2.pt")
model.model.names = {0: target_class}

# 3. 配置设备
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"使用设备: {device} | 目标检测类别: {target_class}")

# 4. 打开摄像头
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    print("无法打开摄像头")
    exit()

# 5. 实时检测
while True:
    ret, frame = cap.read()
    if not ret:
        print("无法获取图像帧，退出...")
        break

    # 模型推理
    results = model(
        frame,
        conf=0.6,
        iou=0.7,  # 提高IOU阈值
        device=device,
        data=str(config_path),
        classes=[0],
        imgsz=640,
        augment=True
    )

    # 结果过滤：仅保留“hand”类别
    filtered_boxes = []
    filtered_confs = []
    filtered_cls = []
    for box in results[0].boxes:
        cls_idx = int(box.cls[0])
        cls_name = model.model.names[cls_idx]
        if target_class in cls_name.lower():
            filtered_boxes.append(box.xyxy[0].cpu().numpy())
            filtered_confs.append(box.conf[0].cpu().numpy())
            filtered_cls.append(cls_idx)

    # 基于皮肤颜色裁剪边界框
    hand_crops = []
    new_filtered_boxes = []
    new_filtered_confs = []
    new_filtered_cls = []
    for bbox, conf, cls_idx in zip(filtered_boxes, filtered_confs, filtered_cls):
        x1, y1, x2, y2 = map(int, bbox)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv_roi, lower_skin, upper_skin)
        skin_ratio = cv2.countNonZero(skin_mask) / (roi.shape[0] * roi.shape[1])
        if skin_ratio > 0.3:
            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                max_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(max_contour)
                new_x1, new_y1 = x1 + x, y1 + y
                new_x2, new_y2 = x1 + x + w, y1 + y + h
                new_x1 = max(new_x1, x1)
                new_y1 = max(new_y1, y1)
                new_x2 = min(new_x2, x2)
                new_y2 = min(new_y2, y2)
                new_filtered_boxes.append([new_x1, new_y1, new_x2, new_y2])
                new_filtered_confs.append(conf)
                new_filtered_cls.append(cls_idx)
                hand_crops.append(roi[y:y+h, x:x+w])

    # 替换为裁剪后的边界框（若有）
    if new_filtered_boxes:
        filtered_boxes = new_filtered_boxes
        filtered_confs = new_filtered_confs
        filtered_cls = new_filtered_cls

    # 绘制结果
    annotated_frame = frame.copy()
    for bbox, conf, cls_idx in zip(filtered_boxes, filtered_confs, filtered_cls):
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{target_class} {conf:.2f}"
        cv2.putText(annotated_frame, label, (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow("YOLOv8-worldv2 精准手部检测", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
config_path.unlink(missing_ok=True)