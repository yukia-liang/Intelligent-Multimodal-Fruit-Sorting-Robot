import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread, Lock
import logging
from datetime import datetime
import cv2
from PIL import Image, ImageTk
import numpy as np
from ultralytics import YOLO
import queue


# ==================== Voice Recognition Thread ====================
class VoiceRecognitionThread(Thread):
    """Voice processing thread that receives voice commands and passes them via queue"""

    def __init__(self, command_queue):
        super().__init__()
        self.command_queue = command_queue
        self.running = True
        self.daemon = True
        # Please modify the serial port according to actual hardware
        self.ser = None
        self.VOICE_MAPPING = {
            b'\xa0': 'apple',
            b'\xa1': 'orange',
            b'\xa2': 'pear'
        }

    def run(self):
        try:
            self.ser = serial.Serial(port="COM8", baudrate=9600, timeout=0.1)
            print(f"Voice module serial port connected: COM8")

            while self.running:
                data = self.ser.read(1)  # Read 1 byte of data
                if data:
                    print(f"Received raw data: {data} (hex: 0x{data.hex()})")
                    if data in self.VOICE_MAPPING:
                        cmd = self.VOICE_MAPPING[data]
                        print(f"Parsed command: {cmd}")
                        # Pass command to main thread via queue
                        self.command_queue.put(cmd)
                time.sleep(0.01)  # Reduce CPU usage

        except Exception as e:
            print(f"Voice module initialization failed: {str(e)}")
            # Put error information in queue as well
            self.command_queue.put(f"ERROR:{str(e)}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()

    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        print("Voice thread stopped")


# ==================== Logging Configuration ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("arm_log.log"), logging.StreamHandler()]
)


# ==================== Serial Communication Protocol Layer ====================
class BusServoController:
    def __init__(self, port='COM9', baudrate=9600):
        """Initialize serial connection"""
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.5  # Read timeout (seconds)
        )

    def _send_command(self, cmd, params):
        """Send protocol command (core communication method)"""
        # Build data frame
        frame = bytearray()
        frame.extend([0x55, 0x55])  # Protocol header
        frame.append(len(params) + 2)  # Data length
        frame.append(cmd)  # Command number
        frame.extend(params)  # Parameter list

        # Send data
        self.ser.write(frame)

        # Process commands that require return values
        if cmd in (0x0F, 0x15):  # Voltage reading (0x0F) and position reading (0x15)
            return self._parse_response()
        return None

    def _parse_response(self):
        """Parse response data packet"""
        # Read frame header
        header = self.ser.read(2)
        if header != b'\x55\x55':
            logging.warning(f"Invalid response header: {header}")
            return None

        # Parse data length and command
        length_byte = self.ser.read(1)
        if not length_byte:
            logging.error("Failed to read data length")
            return None
        length = ord(length_byte)

        cmd_byte = self.ser.read(1)
        if not cmd_byte:
            logging.error("Failed to read command number")
            return None
        cmd = ord(cmd_byte)

        data = self.ser.read(length - 2)  # Subtract already read cmd and length

        # Voltage reading processing
        if cmd == 0x0F:
            if len(data) >= 2:
                return (data[1] << 8) + data[0]  # Little-endian conversion
            logging.error(f"Voltage data length abnormal: {data}")
            return None

        # Servo position reading processing
        elif cmd == 0x15:
            positions = {}
            if len(data) == 0:
                logging.error("Position reading data is empty")
                return positions
            servo_num = data[0]
            for i in range(servo_num):
                idx = 1 + i * 3
                if idx + 2 >= len(data):
                    break
                servo_id = data[idx]
                pos = (data[idx + 2] << 8) + data[idx + 1]
                positions[servo_id] = pos
            return positions

        logging.warning(f"Unknown command response: cmd=0x{cmd:02X}, data={data}")
        return None

    def servo_move(self, servos, time_ms):
        """Multi-servo motion control"""
        params = []
        params.append(len(servos))  # Number of servos
        # Time parameters (little-endian)
        params.extend([time_ms & 0xFF, (time_ms >> 8) & 0xFF])

        # Add parameters for each servo
        for servo_id, pos in servos.items():
            params.append(servo_id)
            # Position parameters (little-endian)
            params.extend([pos & 0xFF, (pos >> 8) & 0xFF])

        return self._send_command(0x03, params)

    def get_voltage(self):
        """Read supply voltage (unit: mV)"""
        return self._send_command(0x0F, [])

    def read_servo_positions(self, servo_ids):
        """Read current positions of multiple servos"""
        params = [len(servo_ids)]
        params.extend(servo_ids)
        return self._send_command(0x15, params)

    def close(self):
        """Close serial connection"""
        if self.ser.is_open:
            self.ser.close()
            logging.info("Serial port closed")


# ==================== Robotic Arm Control Logic Layer ====================
class ArmController:
    def __init__(self, port='COM13'):
        self.ctrl = BusServoController(port=port)
        self.is_running = False  # Motion status flag
        self.lock = Lock()  # Thread safety lock

        # Define servo functions
        self.servo_config = {
            1: {"name": "Gripper", "min": 10, "max": 800},
            2: {"name": "Shoulder", "min": 0, "max": 1000},
            3: {"name": "Elbow", "min": 0, "max": 1000},
            4: {"name": "Wrist", "min": 0, "max": 1000},
            5: {"name": "Bend", "min": 200, "max": 800},
            6: {"name": "Base", "min": 0, "max": 1000}
        }

        # Preset positions
        self.home_position = {1: 62, 2: 506, 3: 505, 4: 498, 5: 514, 6: 869}  # Initial vertical
        self.position_initial_ready = {1: 62, 2: 515, 3: 903, 4: 403, 5: 731, 6: 869}  # Ready posture
        self.position_grab = {1: 368, 2: 515, 3: 903, 4: 403, 5: 731, 6: 869}  # Grab state

        # Release positions for different fruits
        self.fruit_release_positions = {
            "apple": {1: 62, 2: 509, 3: 202, 4: 879, 5: 532, 6: 747},
            "orange": {1: 62, 2: 509, 3: 201, 4: 891, 5: 532, 6: 844},
            "pear": {1: 62, 2: 509, 3: 185, 4: 851, 5: 490, 6: 969}
        }

    def _safety_check(self, positions):
        """Motion range safety check"""
        with self.lock:
            for servo_id, pos in positions.items():
                cfg = self.servo_config.get(servo_id)
                if not cfg:
                    raise ValueError(f"Unknown servo ID: {servo_id}")
                if not (cfg["min"] <= pos <= cfg["max"]):
                    raise ValueError(
                        f"Servo {servo_id}({cfg['name']}) out of safe range: {pos} "
                        f"[Allowed: {cfg['min']}-{cfg['max']}]"
                    )

    def move(self, positions, duration=1500):
        """Execute safe motion"""
        if not self.is_running:
            return False

        try:
            self._safety_check(positions)
            with self.lock:
                self.ctrl.servo_move(positions, duration)
            # Wait for motion to complete (add 20% margin to ensure到位)
            time.sleep(duration / 1000 * 1.2)
            return True
        except Exception as e:
            logging.error(f"Motion failed: {str(e)}")
            return False

    def initialize(self):
        """Return to initial vertical position"""
        logging.info("Returning to initial vertical position")
        return self.move(self.home_position, 2000)

    def pickup_cycle(self, fruit_type="apple", status_callback=None):
        """Complete pick-and-place cycle - Ensure gripper only opens at release point"""
        self.is_running = True
        try:
            if status_callback:
                status_callback(f"Operation completed! - Target fruit: {fruit_type}")

            # Get release position for corresponding fruit
            position_release = self.fruit_release_positions.get(fruit_type, self.fruit_release_positions["apple"])

            # Phase 1: Initial vertical position (gripper open)
            if not self.move(self.home_position, 2000):
                raise Exception("Phase 1 motion failed")
            time.sleep(1)

            # Phase 2: Ready posture (gripper stays open)
            if not self.move(self.position_initial_ready, 1500):
                raise Exception("Phase 2 motion failed")
            time.sleep(1)

            # Phase 3: Close gripper to grab
            grab_position = self.position_initial_ready.copy()
            grab_position[1] = 800  # Close gripper
            if not self.move(grab_position, 1000):
                raise Exception("Phase 3 motion failed")
            time.sleep(1.5)

            # Phase 4: Move to release position (keep gripper closed)
            release_with_claw = position_release.copy()
            release_with_claw[1] = 800  # Keep gripper closed
            if not self.move(release_with_claw, 3000):
                raise Exception("Phase 4 motion failed")
            time.sleep(1)

            # Phase 5: Open gripper at release point
            # Only move gripper to open position, other joints remain unchanged
            release_open_claw = position_release.copy()
            release_open_claw[1] = 300  # Open gripper
            if not self.move(release_open_claw, 1000):
                raise Exception("Phase 5 motion failed")
            time.sleep(1)

            # Phase 6: Return to initial position (gripper stays open)
            if not self.move(self.home_position, 2000):
                raise Exception("Phase 6 motion failed")

            logging.info(f"{fruit_type} pick cycle completed")

        except Exception as e:
            error_msg = f"Operation interrupted: {str(e)}"
            logging.error(error_msg)
            status_callback(error_msg)
            # Exception handling: Move to safe position first then open gripper
            try:
                safe_position = self.home_position.copy()
                if not self.move(safe_position, 1500):
                    # If cannot move to safe position, open gripper directly at current lowest position
                    self.move({1: 300}, 1000)
                else:
                    self.move({1: 300}, 1000)
                time.sleep(0.5)
                self.initialize()
            except Exception as safe_e:
                logging.error(f"Safety recovery failed: {str(safe_e)}")

        finally:
            self.is_running = False

    def stop(self):
        """Stop current motion"""
        with self.lock:
            self.is_running = False
        logging.info("Motion stopped")

    def get_current_status(self):
        """Get current status (voltage + servo positions)"""
        try:
            voltage = self.ctrl.get_voltage()
            positions = self.ctrl.read_servo_positions([1, 2, 3, 4, 5, 6])
            return {
                "voltage": voltage / 1000 if voltage else None,  # Convert to V
                "positions": positions,
                "is_running": self.is_running
            }
        except Exception as e:
            logging.error(f"Status reading failed: {str(e)}")
            return {"voltage": None, "positions": {}, "is_running": self.is_running}


# ==================== YOLO Detection Class ====================
class YOLODetector:
    def __init__(self, model_path=r"vision/model/best.onnx", camera_index=0):
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_MSMF)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.is_running = False
        self.detection_callback = None
        self.frame_callback = None
        self.lock = Lock()

        # Detection parameters
        self.detect_conf = 0.6
        self.center_tolerance = 50
        self.target_fruit = None  # Add target fruit attribute, set by voice command

    def set_target_fruit(self, fruit_type):
        """Set target fruit type (controlled by voice command)"""
        self.target_fruit = fruit_type
        print(f"Target fruit set: {fruit_type}")

    def start_detection(self):
        """Start detection"""
        self.is_running = True
        Thread(target=self._detection_loop, daemon=True).start()

    def stop_detection(self):
        """Stop detection"""
        self.is_running = False

    def is_overlapping(self, box1, box2):
        """Determine if two bounding boxes overlap"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        inter_x1 = max(x1_1, x1_2)
        inter_y1 = max(y1_1, y1_2)
        inter_x2 = min(x2_1, x2_2)
        inter_y2 = min(y2_1, y2_2)

        return inter_x2 > inter_x1 and inter_y2 > inter_y1

    def _detection_loop(self):
        """Detection loop - only focus on target fruit"""
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            # Model inference
            results = self.model(frame, conf=self.detect_conf)
            annotated_frame = frame.copy()
            detections = []
            selected_boxes = []

            # Extract detection results
            for result in results:
                if len(result.boxes) == 0:
                    continue
                for box in result.boxes:
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    conf = box.conf.item()
                    cls = int(box.cls.item())
                    detections.append([[x1, y1, x2, y2], conf, cls])

            # Filter overlapping boxes
            if len(detections) > 0:
                detections_sorted = sorted(detections, key=lambda x: x[1], reverse=True)
                for det in detections_sorted:
                    current_box, current_conf, current_cls = det
                    overlap_flag = False
                    for selected in selected_boxes:
                        if self.is_overlapping(current_box, selected[0]):
                            overlap_flag = True
                            break
                    if not overlap_flag:
                        selected_boxes.append(det)

                # Draw detection boxes - only mark target fruit
                for det in selected_boxes:
                    box, conf, cls = det
                    x1, y1, x2, y2 = map(int, box)
                    class_name = self.model.names[cls].lower()

                    # Only draw boxes for target fruit
                    if self.target_fruit and class_name == self.target_fruit:
                        # Set different colors based on fruit type
                        if class_name == "apple":
                            color = (0, 255, 0)  # Green
                        elif class_name == "orange":
                            color = (0, 165, 255)  # Orange
                        elif class_name == "pear":
                            color = (255, 255, 0)  # Cyan
                        else:
                            color = (255, 0, 0)  # Red
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                        label = f"{class_name} {conf:.2f}"
                        cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Determine if target fruit exists and is centered in width
            current_has_fruit = False
            fruit_is_centered = False
            current_fruit_type = None
            frame_center_x = frame.shape[1] // 2

            # Only process target fruit
            if self.target_fruit:
                for det in selected_boxes:
                    box, conf, cls = det
                    class_name = self.model.names[cls].lower()

                    # Only focus on fruit type specified by voice command
                    if class_name == self.target_fruit and conf >= self.detect_conf:
                        current_has_fruit = True
                        current_fruit_type = class_name
                        fruit_center_x = (box[0] + box[2]) / 2
                        if abs(fruit_center_x - frame_center_x) <= self.center_tolerance:
                            fruit_is_centered = True
                            status_msg = f"📸 {class_name} centered (deviation: {abs(fruit_center_x - frame_center_x):.1f}px)"
                        else:
                            status_msg = f"📸 {class_name} not centered (deviation: {abs(fruit_center_x - frame_center_x):.1f}px)"

                        if self.detection_callback:
                            self.detection_callback(current_has_fruit, fruit_is_centered, current_fruit_type,
                                                    status_msg)
                        break
                else:
                    # No target fruit detected
                    if self.detection_callback:
                        self.detection_callback(False, False, None, f"No {self.target_fruit} detected")
            else:
                # Prompt when no voice command received
                if self.detection_callback:
                    self.detection_callback(False, False, None, "Waiting for voice command...")

            # Draw center reference line
            cv2.line(annotated_frame, (frame_center_x, 0), (frame_center_x, frame.shape[0]),
                     (0, 255, 255), 1)

            # Convert to RGB format for Tkinter display
            annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

            # Callback to display frame
            if self.frame_callback:
                self.frame_callback(annotated_frame_rgb)

            time.sleep(0.03)  # Control frame rate

    def close(self):
        """Release resources"""
        self.is_running = False
        if self.cap.isOpened():
            self.cap.release()


# ==================== GUI Control Layer ====================
class ArmControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Controlled Robotic Arm System")
        self.root.geometry("1200x700")
        self.root.resizable(True, True)

        # Initialize voice recognition queue and thread
        self.voice_command_queue = queue.Queue()
        self.voice_thread = VoiceRecognitionThread(self.voice_command_queue)
        self.voice_thread.start()

        # Initialize robotic arm controller
        self.arm = ArmController(port='COM13')

        # Initialize YOLO detector
        self.detector = YOLODetector(model_path=r"vision/model/best.onnx", camera_index=1)
        self.detector.detection_callback = self._on_detection_update
        self.detector.frame_callback = self._on_frame_update

        self.update_thread = None  # Status update thread
        self.is_gui_running = True  # GUI running flag

        # Detection status
        self.has_fruit = False
        self.fruit_centered = False
        self.current_fruit_type = None
        self.detection_status = tk.StringVar(value="Waiting for voice command...")

        # Voice command related
        self.voice_command = None  # Current voice command
        self.voice_status = tk.StringVar(value="No command")

        # Auto detection status
        self.auto_detection_active = False
        self.auto_detection_thread = None

        # Timer status
        self.countdown_start_time = 0
        self.countdown_active = False
        self.countdown_duration = 18
        self.countdown_fruit_type = None

        # Color configuration
        self.COLOR_RUNNING = "#FF6B6B"  # Running (red)
        self.COLOR_IDLE = "#4ECDC4"  # Idle (cyan)
        self.COLOR_DETECTED = "#90EE90"  # Target detected (light green)
        self.COLOR_AUTO_ACTIVE = "#FFD700"  # Auto mode active (gold)

        # Camera display area dimensions
        self.camera_width = 800
        self.camera_height = 600

        # Create main layout
        self._create_main_layout()

        # Start status update thread
        self._start_update_thread()

        # Start YOLO detection
        self.detector.start_detection()

        # Start voice command check
        self._start_voice_check()

        # Window close event binding
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_main_layout(self):
        """Create main interface layout"""
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Camera display area
        left_frame = ttk.LabelFrame(main_container, text="YOLO Real-time Detection", padding=(10, 5))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_frame.config(width=self.camera_width, height=self.camera_height)
        left_frame.pack_propagate(False)

        # Right panel - Control and status area
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create functional areas
        self._create_camera_display(left_frame)
        self._create_system_status(right_frame)
        self._create_control_buttons(right_frame)
        self._create_log_area(right_frame)

    def _create_camera_display(self, parent):
        """Create camera display area"""
        self.camera_label = ttk.Label(parent, text="Starting camera...", background="black")
        self.camera_label.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Label(info_frame, text="Detection Status:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.detection_info = tk.StringVar(value="Waiting for voice command...")
        ttk.Label(info_frame, textvariable=self.detection_info, foreground="blue").pack(side=tk.LEFT, padx=10)

    def _create_system_status(self, parent):
        """Create system status display area"""
        frame = ttk.LabelFrame(parent, text="System Status", padding=(10, 5))
        frame.pack(fill=tk.X, pady=5)

        # Voltage display
        self.voltage_var = tk.StringVar(value="Unknown")
        ttk.Label(frame, text="System Voltage:").grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.Label(frame, textvariable=self.voltage_var, foreground="#2C3E50", font=("Arial", 10, "bold")).grid(
            row=0, column=1, padx=5, pady=3, sticky=tk.W
        )

        # Motion status display
        self.running_var = tk.StringVar(value="Idle")
        self.status_label = ttk.Label(
            frame, textvariable=self.running_var,
            background=self.COLOR_IDLE, padding=(10, 2), borderwidth=2, relief=tk.SUNKEN
        )
        self.status_label.grid(row=0, column=2, padx=20, pady=3, sticky=tk.W)

        # Detection status display
        self.detection_status_label = ttk.Label(
            frame, textvariable=self.detection_status,
            background=self.COLOR_IDLE, padding=(10, 2), borderwidth=2, relief=tk.SUNKEN
        )
        self.detection_status_label.grid(row=0, column=3, padx=20, pady=3, sticky=tk.W)

        # Voice command display
        self.voice_label = ttk.Label(
            frame, textvariable=self.voice_status,
            background=self.COLOR_IDLE, padding=(10, 2), borderwidth=2, relief=tk.SUNKEN
        )
        self.voice_label.grid(row=0, column=4, padx=20, pady=3, sticky=tk.W)

        frame.grid_columnconfigure(4, weight=1)

    def _create_control_buttons(self, parent):
        """Create control button area"""
        frame = ttk.LabelFrame(parent, text="Control", padding=(10, 5))
        frame.pack(fill=tk.X, pady=5)

        style = ttk.Style()
        style.configure("Control.TButton", font=("Arial", 12), padding=(20, 10))
        style.configure("AutoActive.TButton", font=("Arial", 12, "bold"), padding=(20, 10))

        # Auto detection button
        self.btn_auto = ttk.Button(
            frame, text="Start Auto Detection", command=self._toggle_auto_detection,
            style="Control.TButton"
        )
        self.btn_auto.pack(side=tk.TOP, padx=10, pady=10, fill=tk.X)

        # Instruction text
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, padx=10, pady=10)

        info_text = """
Operation Instructions:
1. Voice command control: Say fruit name (apple/orange/pear)
2. System performs recognition and grasping only for voice-specified fruits
3. Start auto detection to automatically grasp when specified fruit is detected
4. After grasping completes, automatically returns to initial position, waiting for next command
        """
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT,
                               background="#F5F5F5", padding=(10, 10))
        info_label.pack(fill=tk.X)

    def _create_log_area(self, parent):
        """Create log recording area"""
        frame = ttk.LabelFrame(parent, text="Operation Log", padding=(10, 5))
        frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._add_log("System initialization completed, waiting for voice command...")

    def _add_log(self, message):
        """Add log to log area"""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _start_voice_check(self):
        """Start voice command check"""
        self._check_voice_commands()

    def _check_voice_commands(self):
        """Check and process voice commands (executed in main thread)"""
        try:
            while True:
                # Non-blocking way to get command
                command = self.voice_command_queue.get_nowait()
                self._process_voice_command(command)
        except queue.Empty:
            pass
        finally:
            # Check every 100ms
            if self.is_gui_running:
                self.root.after(100, self._check_voice_commands)

    def _process_voice_command(self, command):
        """Process voice command"""
        if command.startswith("ERROR:"):
            error_msg = command[6:]  # Remove "ERROR:" prefix
            self._add_log(f"Voice module error: {error_msg}")
            self.voice_status.set("Voice module error")
            return

        fruit_names = {"apple": "Apple", "orange": "Orange", "pear": "Pear"}
        display_name = fruit_names.get(command, command)

        self.voice_command = command
        self.voice_status.set(f"Command ：{display_name}")
        self.voice_label.configure(background="#90EE90")  # Light green indicates command received

        self._add_log(f"Voice command received: {display_name}")

        # Set YOLO detector's target fruit
        self.detector.set_target_fruit(command)

        # In auto mode, prompt that detection can start after receiving command
        if self.auto_detection_active:
            self._add_log(f"Target fruit updated to {display_name}, detecting...")

    def _update_status_display(self):
        """Update status display"""
        status = self.arm.get_current_status()

        # Update voltage display
        if status["voltage"] is not None:
            self.voltage_var.set(f"{status['voltage']:.2f}V")
        else:
            self.voltage_var.set("Read failed")

        # Update motion status
        if status["is_running"]:
            self.running_var.set("Moving")
            self.status_label.configure(background=self.COLOR_RUNNING)
            self.btn_auto.configure(state=tk.DISABLED)
        else:
            self.running_var.set("Idle")
            self.status_label.configure(background=self.COLOR_IDLE)
            self.btn_auto.configure(state=tk.NORMAL)

        # Check if countdown ended
        if self.countdown_active:
            elapsed = time.time() - self.countdown_start_time
            if elapsed >= self.countdown_duration:
                self._trigger_auto_pickup()

    def _status_update_loop(self):
        """Status update loop"""
        while self.is_gui_running:
            self.root.after(0, self._update_status_display)
            time.sleep(0.5)

    def _start_update_thread(self):
        """Start status update thread"""
        self.update_thread = Thread(target=self._status_update_loop, daemon=True)
        self.update_thread.start()

    def _toggle_auto_detection(self):
        """Toggle auto detection mode"""
        if self.arm.is_running:
            messagebox.showwarning("Warning", "Robotic arm is moving, cannot perform this operation")
            return

        if not self.auto_detection_active:
            # Check if voice command received before starting auto detection
            if not self.voice_command:
                messagebox.showinfo("Prompt", "Please specify target fruit via voice command first")
                return

            self.auto_detection_active = True
            self.btn_auto.configure(text="Stop Auto Detection", style="AutoActive.TButton")
            self._add_log(f"Auto detection mode started, target fruit: {self.voice_command}")
        else:
            self.auto_detection_active = False
            self.btn_auto.configure(text="Start Auto Detection", style="Control.TButton")
            self._add_log("Auto detection mode stopped")
            self.countdown_active = False

    def _trigger_auto_pickup(self):
        """Trigger auto pickup"""
        if not self.auto_detection_active or self.arm.is_running or not self.voice_command:
            return

        self.countdown_active = False
        self._add_log(f"Automatically triggering {self.voice_command} pickup...")
        self.arm.pickup_cycle(fruit_type=self.voice_command, status_callback=self._update_phase)

    def _update_phase(self, phase_text):
        """Update current phase"""
        self.root.after(0, lambda: self._add_log(phase_text))

    def _on_detection_update(self, has_fruit, fruit_is_centered, fruit_type, status_msg):
        """Handle detection result update"""
        self.has_fruit = has_fruit
        self.fruit_centered = fruit_is_centered
        self.current_fruit_type = fruit_type

        # Update detection status display
        if has_fruit:
            if fruit_is_centered:
                self.detection_status.set(f"{fruit_type} centered")
                self.detection_status_label.configure(background=self.COLOR_DETECTED)

                # In auto detection mode, start countdown
                if (self.auto_detection_active and
                        not self.countdown_active and
                        not self.arm.is_running and
                        self.voice_command == fruit_type):
                    self.countdown_start_time = time.time()
                    self.countdown_active = True
                    self.countdown_fruit_type = fruit_type
            else:
                self.detection_status.set(f"{fruit_type} not centered")
                self.detection_status_label.configure(background=self.COLOR_IDLE)
        else:
            self.detection_status.set(status_msg)
            self.detection_status_label.configure(background=self.COLOR_IDLE)

        self.detection_info.set(status_msg)

    def _on_frame_update(self, frame_rgb):
        """Handle frame update"""
        img = Image.fromarray(frame_rgb)
        img_ratio = img.width / img.height
        target_ratio = self.camera_width / self.camera_height

        if img_ratio > target_ratio:
            new_width = self.camera_width
            new_height = int(self.camera_width / img_ratio)
        else:
            new_height = self.camera_height
            new_width = int(self.camera_height * img_ratio)

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.camera_label.imgtk = imgtk
        self.camera_label.configure(image=imgtk)

    def _on_close(self):
        """Window close handling"""
        self.is_gui_running = False
        self.auto_detection_active = False

        if self.update_thread:
            self.update_thread.join(timeout=1.0)

        # Stop all threads and resources
        self.detector.stop_detection()
        self.detector.close()
        self.voice_thread.stop()
        self.arm.stop()
        self.arm.ctrl.close()
        self.root.destroy()


# ==================== Main Program ====================
if __name__ == "__main__":
    root = tk.Tk()
    app = ArmControlGUI(root)
    root.mainloop()
