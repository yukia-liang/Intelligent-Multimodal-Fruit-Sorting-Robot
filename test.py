from ultralytics import YOLO
import os

# 初始化模型
model = YOLO('yolov8s-worldv2.pt')

# 设置检测类别（取消注释并修改为您的实际类别）
model.set_classes(["rock", "stone"])

# 定义输入输出路径

input_dir = './rock/data'  # 输入图片目录
save_dir = './rock'    # 输出目录

# 自动创建输出目录
os.makedirs(save_dir, exist_ok=True)

# 执行预测并保存结果
results = model.predict(
    source=input_dir,
    save=True,               # 保存检测结果图片
    save_txt=True,           # 保存标签文件（可选）
    project=save_dir,        # 指定输出根目录
    name='output',          # 子目录名称（最终路径：./run/output_image/predict）
    conf=0.1,
    exist_ok=True            # 允许覆盖已有结果
)

print(f"检测完成！结果保存在: {os.path.abspath(save_dir)}")