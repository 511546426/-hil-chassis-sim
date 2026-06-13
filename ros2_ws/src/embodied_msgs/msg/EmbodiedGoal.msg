# P3-C2：语义任务目标（对齐 embodied_core::TaskGoal）
std_msgs/Header header

uint8 POINT=0
uint8 OBJECT=1
uint8 PUSH_RED_BOX=2
uint8 kind

float64 x
float64 y
string object_name
float64 standoff
