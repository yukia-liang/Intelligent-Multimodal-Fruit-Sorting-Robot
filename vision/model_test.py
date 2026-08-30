from ultralytics import YOLO
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from pathlib import Path
from PIL import Image

def analyze_test_set(model_path, data_yaml, save_dir='test_analysis'):
    try:
        # 路径安全校验
        model_path = Path(model_path).resolve()
        data_yaml = Path(data_yaml).resolve()
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 加载模型
        model = YOLO(str(model_path))

        # 运行验证并生成基础图表
        results = model.val(
            data=str(data_yaml),
            split='test',
            conf=0.5,
            iou=0.5,
            plots=True,        # 生成PNG图表
            save_json=True,    # 保存JSON结果
            save_hybrid=False, # 关闭混合模式
            name=str(save_dir)
        )

        # 自定义混淆矩阵生成
        conf_matrix = results.confusion_matrix.matrix  # 直接获取混淆矩阵数据
        classes = list(model.names.values())

        plt.figure(figsize=(10, 8))
        sns.heatmap(conf_matrix, annot=True, fmt='.2f', cmap='Blues',
                    xticklabels=classes,
                    yticklabels=classes)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Normalized Confusion Matrix')
        plt.savefig(save_dir / 'custom_confusion_matrix.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"分析完成！结果保存在: {save_dir}")

    except Exception as e:
        print(f"错误发生: {str(e)}")
        print("排查建议:")
        print("1. 确认模型路径和数据YAML文件存在")
        print("2. 检查测试集标签文件是否与图像对应")

if __name__ == '__main__':
    # 配置路径（根据实际情况修改）
    config = {
        'model_path': Path("D:/ultralytics/runs/detect/train17/weights/best.pt"),
        'data_yaml': Path("D:/ultralytics/data/data.yaml"),
        'save_dir': Path("D:/ultralytics/test_analysis_results")
    }

    analyze_test_set(**config)
