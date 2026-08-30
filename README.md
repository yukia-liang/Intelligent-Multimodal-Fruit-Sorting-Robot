# Intelligent Multimodal Fruit Sorting Robot

An integrated multimodal robotic sorting system combining **visual perception, offline voice interaction, command understanding, real-time image processing, GUI monitoring, and robotic-arm execution**.

The project follows a perception–decision–execution workflow:

`	ext
Offline Voice Command
        ↓
Command / Target Parsing
        ↓
YOLO Visual Perception
        ↓
Target Verification
        ↓
Robotic Arm Control
        ↓
Automatic Grasping & Sorting
`

## System Demo

<p align="center">
  <img src="assets/demo/system_demo.gif"
       alt="Intelligent Multimodal Fruit Sorting Robot Demo"
       width="760">
</p>

Full-quality demo:

ssets/demo/system_demo.mp4

## Repository Structure

`	ext
Intelligent-Multimodal-Fruit-Sorting-Robot/
│
├── README.md
├── main.py
│
├── vision/
│   ├── model/
│   │   └── best.onnx
│   ├── onnx_inference.py
│   ├── export_onnx.py
│   ├── simplify_onnx.py
│   ├── hand_detection.py
│   └── model_test.py
│
├── speech/
│   └── README.md
├── audio/
│   └── README.md
├── interaction/
│   └── README.md
├── robot/
│   └── arm_controller.py
├── gui/
│   └── README.md
├── training/
│   └── train_yolo.py
├── tools/
│   └── check_annotations.py
├── configs/
│   └── hardware.example.yaml
├── assets/
│   ├── images/
│   └── demo/
│       ├── system_demo.gif
│       └── system_demo.mp4
│
├── requirements.txt
├── .gitignore
└── LICENSE
`

## Main System

main.py is the complete integrated runtime.

It currently contains:

- Offline voice-command reception
- Command-to-fruit mapping
- YOLO-based visual detection
- OpenCV camera acquisition
- Tkinter real-time GUI
- Multi-threaded task coordination
- Robotic-arm serial control
- Automatic fruit pickup cycles

## Modalities

### Vision
The visual subsystem performs real-time image acquisition and YOLO-based fruit detection.

### Speech
An offline voice module provides recognized commands to the Python system through serial communication.

### Audio
The current implementation relies on the offline speech hardware for acoustic front-end processing. The udio/ directory is reserved for future direct waveform or microphone-array processing.

### Interaction
Recognized commands are mapped to sorting targets and dispatched to the vision and execution layers.

### Robot
The robotic-arm subsystem communicates with the servo controller through serial communication and executes predefined grasping sequences.

### GUI
The GUI displays the camera feed, target information, voice-command state, detection state, logs, and robotic-arm status.

## Supported Target Commands

- Apple
- Orange
- Pear

## Installation

`ash
pip install -r requirements.txt
`

## Run

From the repository root:

`ash
python main.py
`

Before running, make sure the serial ports and camera index match your hardware.

Example values are documented in:

configs/hardware.example.yaml

## Model

The packaged ONNX model is stored at:

ision/model/best.onnx

## Notes

The current release intentionally keeps the complete working integration in main.py instead of aggressively splitting the runtime into many dependent Python modules. This keeps the original integrated system easy to inspect and reduces the risk of breaking hardware-dependent behavior, while the repository structure clearly separates vision, speech, audio, interaction, robot, GUI, configuration, training, and demonstration assets.

## License

See LICENSE.
