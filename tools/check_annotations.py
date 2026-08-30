import os
import random
import cv2
import numpy as np

# ---------- 替换为你的路径 ----------
# 图像所在目录
images_dir = r"D:\pythonnn\class program\hand_dataset\images"  # 例如："D:/pythonn/class program/split_dataset/train/images"
# 标注txt所在目录（与图像目录对应）
labels_dir = r"D:\pythonnn\class program\hand_dataset\labels"  # 例如："D:/pythonn/class program/split_dataset/train/labels"
# 输出可视化结果的目录（若需保存）
output_dir = "visualized"
os.makedirs(output_dir, exist_ok=True)
# -----------------------------------

# 获取所有图像文件名
image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
# 随机选10张
random_images = random.sample(image_files, 10)

for img_name in random_images:
    img_path = os.path.join(images_dir, img_name)
    label_name = os.path.splitext(img_name)[0] + ".txt"
    label_path = os.path.join(labels_dir, label_name)

    # 读取图像
    img = cv2.imread(img_path)
    if img is None:
        print(f"警告：无法读取图像 {img_path}")
        continue
    height, width = img.shape[:2]

    # 读取YOLO标注txt
    if os.path.exists(label_path):
        with open(label_path, "r") as f:
            lines = f.readlines()
    else:
        print(f"警告：标注文件 {label_path} 不存在")
        continue

    for line in lines:
        line = line.strip().split()
        if len(line) < 5:
            continue
        # YOLO格式：class_id cx cy w h（归一化坐标）
        class_id, cx, cy, w, h = map(float, line)
        # 转换为像素坐标
        x1 = int((cx - w / 2) * width)
        y1 = int((cy - h / 2) * height)
        x2 = int((cx + w / 2) * width)
        y2 = int((cy + h / 2) * height)
        # 绘制矩形框和类别标签
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"class_{int(class_id)}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 显示图像（可选，若需实时查看）
    cv2.imshow("YOLO Annotations", img)
    cv2.waitKey(0)  # 按任意键继续下一张
    # 保存可视化图像（可选）
    cv2.imwrite(os.path.join(output_dir, f"visualized_{img_name}"), img)

cv2.destroyAllWindows()