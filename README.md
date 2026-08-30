# Intelligent Multimodal Fruit Sorting Robot System

An intelligent fruit-sorting robot that integrates **YOLO-World visual perception**, **offline voice interaction**, and **robotic-arm execution** in a perception–decision–execution pipeline.

The system is designed for low-cost, network-independent agricultural sorting and supports real-time fruit recognition, target localization, coordinate verification, and automated grasping.

---

## 🎥 System Demo

<p align="center">
  <img src="assets/videos/multimodal_sorting_robot_system_demo.gif"
       alt="Intelligent Multimodal Fruit Sorting Robot System Demo"
       width="900">
</p>

<p align="center">
  <em>YOLO-World visual perception + offline voice interaction + robotic-arm fruit sorting.</em>
</p>

> The animated demo above is displayed directly in the README.  
> Full-quality recording: `assets/videos/multimodal_sorting_robot_system_demo.mp4`

---

## Project Overview

The system combines:

- **YOLO-World / YOLOv8n-World visual recognition**
- **Offline voice command interaction**
- **Robotic-arm control**
- **Coordinate mapping for fruit grasping**
- **Multi-threaded software integration**
- **ONNX deployment for efficient inference**

The overall workflow is:

```text
Voice Command
    ↓
GUI / Task Dispatch
    ↓
YOLO-World Visual Detection
    ↓
Target Verification & Coordinate Mapping
    ↓
Robotic Arm Control
    ↓
Fruit Grasping and Sorting
```

---

## Key Features

### 1. Visual Perception
The camera captures fruit images and the YOLO-World model predicts:

- Fruit category
- Bounding box
- Confidence score
- Target center position

The system additionally verifies whether the target is stable and located inside the robotic arm's graspable workspace.

### 2. Offline Voice Interaction
The voice module provides a network-independent human–computer interaction interface.

Example commands include:

```text
grab apple
grab orange
grab pear
```

The detected command is converted into a target category and sent to the visual perception module.

### 3. Robotic Arm Execution
After visual verification, the system converts image coordinates into physical coordinates and generates the corresponding grasping action.

A typical grasping sequence is:

```text
Move above target
    ↓
Move to grasping height
    ↓
Close gripper
    ↓
Move to sorting position
    ↓
Release fruit
    ↓
Return to initial position
```

### 4. Multi-threaded System Integration
The software system contains multiple cooperating threads:

- Main GUI thread
- Voice-recognition thread
- YOLO visual-detection thread
- Robotic-arm control thread

This modular design improves responsiveness and keeps perception, interaction, and execution synchronized.

---

## Performance

The project report records the following experimental results:

| Metric | Result |
|---|---:|
| YOLO-World mAP@50 | **0.99499** |
| Average detection time | **181.2 ms / image** |
| Test images for inference-speed evaluation | **500** |
| Coordinate-mapping grasping success rate | **95.7%** |
| Number of on-site grasping attempts | **50** |

The model was trained for **100 epochs** on a fruit-recognition dataset built for the project.

---

## My Contribution

My main work in this project focused on the visual perception pipeline:

- Researched existing fruit-sorting technologies
- Built and preprocessed a **3,000-image fruit dataset**
- Developed the YOLO-World-based visual recognition module
- Trained and validated the detection model
- Evaluated recognition performance
- Exported/deployed the model through **ONNX**
- Improved real-time fruit recognition and sorting accuracy

---

## Repository Structure

```text
YOLO-World-project/
│
├── dataset/
│   └── data.yaml
│
├── demo/
│   ├── gradio_demo.py
│   ├── image_demo.py
│   ├── image_prompt_demo.py
│   ├── simple_demo.py
│   └── video_demo.py
│
├── deploy/
│   ├── export_onnx.py
│   ├── onnx_demo.py
│   └── easydeploy/
│
├── docs/
│   ├── installation.md
│   ├── finetuning.md
│   ├── deploy.md
│   └── ...
│
├── results/
│   ├── confusion_matrix.png
│   ├── results.csv
│   └── results.png
│
├── tools/
│   ├── train.py
│   ├── test.py
│   └── reparameterize_yoloworld.py
│
├── yolo_world/
│   ├── datasets/
│   ├── engine/
│   └── models/
│
├── train.py
├── test.py
├── visual_detect.py
├── pt2onnx.py
├── onnx_detec.py
└── pyproject.toml
```

---

## Environment

The project report used the following training/inference environment:

```text
GPU: NVIDIA RTX A4000
PyTorch: 1.12.0
CUDA: 11.3
```

For the current repository, please also check:

```text
docs/installation.md
pyproject.toml
```

for the latest dependency configuration.

---

## Training

The repository contains training scripts at both the project root and under `tools/`.

Example:

```bash
python train.py
```

Dataset configuration:

```text
dataset/data.yaml
```

---

## Evaluation

Example:

```bash
python test.py
```

Training and evaluation outputs can be found under:

```text
results/
```

Example result files:

```text
results/results.png
results/confusion_matrix.png
results/results.csv
```

---

## Visualization

For image-based visual detection:

```bash
python visual_detect.py
```

Additional demos are available in:

```text
demo/
```

including image, video, prompt-based, notebook, and Gradio examples.

---

## ONNX Deployment

The repository includes scripts for model export and ONNX inference:

```bash
python pt2onnx.py
python onnx_detec.py
```

Additional deployment utilities are available under:

```text
deploy/
```

---

## System Architecture

The complete multimodal sorting system follows a three-stage architecture:

### Perception Layer
- RGB camera
- YOLO-World fruit detection
- Offline voice command acquisition

### Decision Layer
- Target-category parsing
- Detection verification
- Coordinate mapping
- Task planning

### Execution Layer
- Robotic-arm motion
- Gripper control
- Fruit placement
- Conveyor coordination

---

## Application Scenarios

Potential application scenarios include:

- Small and medium-sized fruit sorting facilities
- Agricultural automation
- Offline sorting in areas with limited network connectivity
- Fruit classification and grading
- Robotic picking and manipulation

Future extensions may include:

- Defect detection
- Ripeness classification
- Size grading
- Additional fruit categories
- Faster robotic-arm response
- More robust recognition under occlusion and illumination changes

---

## Contributors

This project was developed as part of the **CE201 Team Project Challenge**.

Advisers:

- Junhua Li
- Cheng Liu

Team members:

- Liyang Yu
- Yajie Yuan
- Yixuan Feng
- Yichun Zhang
- Siyun Xie
- Yupu Liu

---

## License

This repository follows the license included in the project root:

```text
LICENSE
```

Please refer to that file for detailed licensing information.
