from ultralytics import YOLO
import onnx
import os


def export_onnx_for_raspberrypi(model_path, output_path):
    # 加载模型
    model = YOLO(model_path)

    # 导出ONNX模型（移除output参数，改用filename参数）
    exported_model = model.export(
        format="onnx",
        filename=output_path,  # 新版本用filename指定输出路径
        opset=12,  # 低版本opset保证树莓派兼容性
        dynamic=False,  # 关闭动态维度
        imgsz=640,  # 输入尺寸
        simplify=True,  # 简化模型
        optimize=True  # 优化模型
    )

    # 验证导出的模型
    onnx_model = onnx.load(exported_model)
    onnx.checker.check_model(onnx_model)
    print(f"模型导出成功：{exported_model}")
    print(f"模型大小：{os.path.getsize(exported_model) / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    # 训练好的权重路径
    model_path = "./runs/detect/train13/weights/best.pt"
    # 输出路径（不含后缀，会自动添加.onnx）
    output_path = "./yoloworld_fruit_raspi"  # 注意这里去掉了.onnx后缀

    export_onnx_for_raspberrypi(model_path, output_path)
