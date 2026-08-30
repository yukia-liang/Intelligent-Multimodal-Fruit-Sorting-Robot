from ultralytics import YOLO
import os

def main():
    # 初始化模型
    model = YOLO("yolov8n.pt")

    # 确保 data.yaml 路径正确（假设文件在项目根目录）
    data_yaml = "D:/ultralytics/data/data.yaml"  # 直接使用文件名（如果文件在项目根目录）

    # 训练配置
    results = model.train(
        data=data_yaml,
        epochs=100,
        imgsz=640,
        batch=4,
        device="cpu",
        workers=0,
        optimizer="Adam",
        lr0=1e-4,
        pretrained=True,
        single_cls=False,
        verbose=True,    # 输出详细日志
        plots=True,      # 生成训练图表
        save_json=True,  # 保存JSON格式评估结果
        # 数据增强参数直接在此处配置（示例）
        mosaic=1,
        mixup=0.2,
        copy_paste=0.3,
        hsv_h=0.02,
        hsv_s=0.8,
        hsv_v=0.4
    )

    # 使用测试集评估模型性能
    test_results = model.val(
        data=data_yaml,
        split='test',  # 明确指定使用测试集
        conf=0.5,
        iou=0.5
    )

    # 对测试集进行预测（可选）
    test_image_dir = os.path.join("D:/ultralytics/data/fruit", "images/test")
    model.predict(
        source=test_image_dir,
        save=True,
        save_txt=True,
        save_conf=True
    )

if __name__ == "__main__":
    main()
