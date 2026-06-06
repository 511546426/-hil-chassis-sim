# 小汽车控制指令（域控 → 模拟底盘 / CAN 下行等价）

float64 target_linear_x        # 目标线速度 (m/s)，前进方向
float64 target_steering_angle  # 目标前轮转向角 (rad)，左正右负
bool emergency_brake           # 急停
