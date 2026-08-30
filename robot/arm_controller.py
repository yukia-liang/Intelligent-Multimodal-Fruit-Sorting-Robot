import serial
import time

# ==================== 串口通信协议层 ====================
class BusServoController:
    def __init__(self, port='COM13', baudrate=9600):
        """初始化串口连接
        Args:
            port: 串口设备路径，Windows系统一般为COMx，Linux为/dev/ttyUSBx
            baudrate: 波特率，需与舵机控制器匹配
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.5  # 读取超时时间（秒）
        )

    def _send_command(self, cmd, params):
        """发送协议指令（核心通信方法）"""
        # 构建数据帧
        frame = bytearray()
        frame.extend([0x55, 0x55])        # 协议头
        frame.append(len(params) + 2)     # 数据长度
        frame.append(cmd)                 # 指令号
        frame.extend(params)              # 参数列表

        # 发送数据
        self.ser.write(frame)

        # 处理需要返回值的指令
        if cmd in (0x0F, 0x15):  # 电压读取(0x0F)和位置读取(0x15)
            return self._parse_response()
        return None

    def _parse_response(self):
        """解析返回数据包"""
        # 读取帧头
        header = self.ser.read(2)
        if header != b'\x55\x55':
            print("[警告] 无效的响应头:", header)
            return None

        # 解析数据长度和指令
        length = ord(self.ser.read(1))
        cmd = ord(self.ser.read(1))
        data = self.ser.read(length - 2)  # 减去已读的cmd和length

        # 电压读取处理
        if cmd == 0x0F:
            if len(data) >= 2:
                return (data[1] << 8) + data[0]  # 小端格式转换
            print("[错误] 电压数据长度异常:", data)
            return None

        # 舵机位置读取处理
        elif cmd == 0x15:
            positions = {}
            servo_num = data[0]
            for i in range(servo_num):
                idx = 1 + i*3
                if idx+2 >= len(data):
                    break
                servo_id = data[idx]
                pos = (data[idx+2] << 8) + data[idx+1]
                positions[servo_id] = pos
            return positions

        print(f"[警告] 未知指令响应: cmd=0x{cmd:02X}, data={data}")
        return None

    def servo_move(self, servos, time_ms):
        """多舵机运动控制
        Args:
            servos: 字典格式 {舵机ID: 目标位置(0-1000)}
            time_ms: 运动时间（毫秒）
        """
        params = []
        params.append(len(servos))  # 舵机数量
        # 时间参数（小端格式）
        params.extend([time_ms & 0xFF, (time_ms >> 8) & 0xFF])

        # 添加各舵机参数
        for servo_id, pos in servos.items():
            params.append(servo_id)
            # 位置参数（小端格式）
            params.extend([pos & 0xFF, (pos >> 8) & 0xFF])

        return self._send_command(0x03, params)

    def get_voltage(self):
        """读取供电电压（单位：mV）"""
        return self._send_command(0x0F, [])

    def read_servo_positions(self, servo_ids):
        """读取多个舵机当前位置
        Args:
            servo_ids: 需要读取的舵机ID列表
        """
        params = [len(servo_ids)]
        params.extend(servo_ids)
        return self._send_command(0x15, params)

# ==================== 机械臂控制逻辑层 ====================
class ArmController:
    def __init__(self):
        self.ctrl = BusServoController(port='COM13')  # 确认实际串口号

        # 定义舵机功能（根据实际硬件配置）
        self.servo_config = {
            1: {"name": "夹爪", "min": 10, "max": 800},
            2: {"name": "肩关节", "min": 0, "max": 1000},
            3: {"name": "肘关节", "min": 0, "max": 1000},
            4: {"name": "腕关节", "min": 0, "max": 1000},
            5: {"name": "关节", "min": 0, "max": 1000},
            6: {"name": "底座", "min": 0, "max": 1000}
        }

        # 预设位置（根据实际机械结构校准）
        self.home_position = {
            1: 300,   # 夹爪全开
            2: 500,  # 肩部中位
            3: 685,  # 肘部中位
            4: 295,  # 腕部中位
            5: 290,
            6: 895   # 底座中位
        }

        self.position_a = {
            1: 365,
            2: 505,  # 肩部下压
            3: 685,  # 肘部抬起
            4: 295,  # 腕部调整
            5: 420,
            6: 895   # 底座右转
        }

        self.position_b = {
            1: 760,
            2: 505,  # 肩部抬起
            3: 685,  # 肘部弯曲
            4: 295,  # 腕部复位
            5: 420,
            6: 895   # 底座左转
        }

        self.position_c = {
            1: 120,
            2: 505,  # 肩部下压
            3: 685,  # 肘部抬起
            4: 295,  # 腕部调整
            5: 330,
            6: 505   # 底座右转
        }

    def _safety_check(self, positions):
        """运动范围安全检查"""
        for servo_id, pos in positions.items():
            cfg = self.servo_config.get(servo_id)
            if not cfg:
                raise ValueError(f"未知舵机ID: {servo_id}")
            if not (cfg["min"] <= pos <= cfg["max"]):
                raise ValueError(
                    f"舵机{servo_id}({cfg['name']})超出安全范围: {pos} "
                    f"[允许范围: {cfg['min']}-{cfg['max']}]"
                )

    def move(self, positions, duration=1500):
        """执行安全运动
        Args:
            positions: 目标位置字典
            duration: 运动时间（毫秒）
        """
        # 排除5号舵机
        # filtered = {k:v for k,v in positions.items() if k != 5}
        # 安全检查
        self._safety_check(filtered)
        # 执行移动
        self.ctrl.servo_move(filtered, duration)
        # 等待运动完成（时间+20%余量）
        time.sleep(duration/1000 * 1.2)

    def initialize(self):
        """返回初始位置"""
        print("[动作] 初始化位置...")
        self.move(self.home_position)

    def pickup_cycle(self):
        """完整的抓取-放置循环"""
        try:
            print("\n=== 开始抓取循环 ===")
            # 阶段1：移动到A点并抓取
            print("-> 前往抓取位置(A点)")
            self.move(self.position_a, 2000)
            print("-> 闭合夹爪")
            self.move({1: 800}, 800)  # 闭合动作

            # 阶段2：移动到B点并释放
            print("\n-> 前往放置位置(B点)")
            self.move(self.position_b, 2500)
            print("-> 松开夹爪")
            self.move({1: 10}, 800)   # 释放动作

            # 阶段2：移动到B点并释放
            print("\n-> 前往放置位置(B点)")
            self.move(self.position_c, 2500)
            print("-> 松开夹爪")
            self.move({1: 10}, 800)   # 释放动作

            # 阶段3：返回初始位置
            print("\n-> 返回初始位置")
            self.initialize()

            print("\n=== 操作完成 ===")
        except Exception as e:
            print(f"! 操作中断: {str(e)}")
            self.initialize()

# ==================== 主程序 ====================
if __name__ == "__main__":
    # 初始化机械臂
    arm = ArmController()

    # 连接测试
    print("正在连接舵机控制器...")
    voltage = arm.ctrl.get_voltage()
    if voltage:
        print(f"系统电压: {voltage/1000:.2f}V")
    else:
        print("电压读取失败，请检查硬件连接！")

    # 执行初始化
    arm.initialize()

    # 显示初始位置
    print("初始位置:", arm.ctrl.read_servo_positions([1,2,3,4,6]))

    # 执行完整工作循环
    arm.pickup_cycle()
