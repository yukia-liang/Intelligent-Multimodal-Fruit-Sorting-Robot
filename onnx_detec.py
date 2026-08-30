import onnxruntime as ort
import numpy as np

# 加载模型
session = ort.InferenceSession("best.onnx")
input_name = session.get_inputs()[0].name
output_names = [o.name for o in session.get_outputs()]

# 构造随机输入（形状与模型输入一致，如 1x3x672x672）
fake_input = np.random.randn(1, 3, 672, 672).astype(np.float32)

# 推理
outputs = session.run(output_names, {input_name: fake_input})
print("模型推理成功，输出形状：", [o.shape for o in outputs])

