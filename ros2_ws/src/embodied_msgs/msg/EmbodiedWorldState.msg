# 仿真节点发布的完整观测（供大脑订阅）

std_msgs/Header header

# 底盘（与 /chassis_state 冗余，便于单话题订阅）
float64 base_x
float64 base_y
float64 base_yaw
float64 base_vx
float64 base_steer

# 机械臂
float64 arm_shoulder
float64 arm_elbow
float64 arm_wrist
float64 gripper          # 0=张开, 1=闭合

# 可动物体（按场景中 body 名）
geometry_msgs/Pose[] object_poses
string[]             object_names

# 接触/任务相关
bool gripper_touching_object
string touched_object_name   # 空串表示无接触
