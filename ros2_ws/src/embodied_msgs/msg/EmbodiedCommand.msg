# 具身智能体控制指令

# --- 移动底盘 ---
float64 target_linear_x
float64 target_steering_angle
bool emergency_brake

# --- 机械臂关节角 (rad) ---
float64 arm_shoulder
float64 arm_elbow
float64 arm_wrist

# --- 夹爪：0.0=张开, 1.0=闭合 ---
float64 gripper
