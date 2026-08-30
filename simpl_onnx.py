from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic(
    'yoloworld.onnx',
    'yoloworld_quantized.onnx',
    weight_type=QuantType.INT8
)