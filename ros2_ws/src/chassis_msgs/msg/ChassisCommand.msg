# 差速底盘控制指令（域控 → 模拟底盘 / CAN 下行等价）

float64 target_linear_x       # 目标线速度 (m/s)，车体坐标系前进方向
float64 target_angular_z      # 目标角速度 (rad/s)，绕 z 轴
bool emergency_brake          # 急停：true 时按急停减速度快速刹停
