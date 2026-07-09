# LubanVision 系统设计

## 1. 项目目标

构建一个可以通过SSH完成开发、部署和诊断的ROS 2主动视觉机器人。摄像头观察ArUco目标，
控制器根据目标中心与画面中心的误差调整云台，使目标持续保持在视野中心。

首版使用ArUco标记建立稳定、可测的视觉闭环。人体检测、YOLO和RK3588 NPU属于验收后
的增强功能，不得阻塞首版交付。

## 2. 闭环结构

```text
USB Camera
    │ sensor_msgs/Image
    ▼
aruco_detector ──→ /target/observation
                       │ center_x, center_y, visible, id
                       ▼
                 gimbal_controller
                 PID + 状态机 + 限位
                       │ /gimbal/command
                       ▼
                 pca9685_hardware
                       │ Linux I²C / PWM
                       ▼
                 SG90 pan / tilt
                       │ 改变摄像头方向
                       └──────────────→ Camera视觉反馈
```

SG90没有位置反馈，但视觉误差构成外环反馈。舵机目标角度和状态用于诊断，不能当作真实机械
角度测量。首版先完成单轴Pan，双轴Tilt复用同一接口。

## 3. 三机架构

- MacBook：Git主仓、项目文档、任务和问题管理、SSH运维。
- Windows/WSL2：ROS 2桌面开发、RViz、曲线观察、rosbag分析和离线测试。
- RK3588：Ubuntu 22.04 Server，运行相机、检测、控制、I²C硬件和systemd。

运行闭环不得依赖Mac或Windows在线。网络中断只影响远程观察，不影响RK本地控制；远程
命令超时后保持当前安全状态或回中。

## 4. ROS 2包规划

- `lubanvision_interfaces`：目标观测、云台状态以及启停/回中服务。
- `lubanvision_camera_cpp`：低开销V4L2相机输入、raw图像发布和速率探针。
- `lubanvision_vision`：Python视觉实验、ArUco检测、标注图像和检测统计。
- `lubanvision_control`：PID、目标丢失状态机、限位和模拟云台。
- `lubanvision_hardware`：PCA9685 I²C访问、PWM/角度标定和硬件诊断。
- `lubanvision_description`：`base_link`、`pan_link`、`tilt_link`、`camera_link`和TF。
- `lubanvision_bringup`：YAML参数、launch、rosbag配置与部署。

## 5. ROS 2接口

建议接口：

| 接口 | 类型 | 说明 |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | 原始图像 |
| `/target/observation` | 自定义消息 | ID、中心、归一化误差、可见状态 |
| `/target/debug_image` | `sensor_msgs/Image` | 带检测框调试图 |
| `/gimbal/command` | 自定义消息 | Pan/Tilt目标角度 |
| `/gimbal/state` | 自定义消息 | 命令角度、状态、I²C健康度 |
| `/tracking/enabled` | `std_msgs/Bool` | 显式启停跟踪 |
| `/tracking/reset` | `std_srvs/Trigger` | 清积分并回中 |

目标观测带相机时间戳；控制器忽略过期观测。参数包括目标ID、图像尺寸、PID、最大速度、
角度范围、丢失超时、回中时间和扫描范围，全部由YAML管理。

## 6. 控制策略

单轴初版：

```text
error_x = (target_x - image_center_x) / image_width
pan_delta = -(Kp*error_x + Ki*integral + Kd*derivative)
```

- 目标位于死区内时不更新角度，减少舵机抖动。
- 每周期限制最大角度增量，避免瞬间大动作。
- 输出经过机械角度限位和PWM限位双重裁剪。
- 目标丢失短于`hold_timeout`时保持；随后缓慢回中。
- 自动扫描是后续可选模式，默认关闭。
- 切换目标或重新捕获时清理PID积分，防止积分突变。

## 7. 硬件与电气

PCA9685由鲁班猫I²C控制，逻辑侧使用3.3V；SG90使用独立5V电源。舵机启动电流可能造成
电压下降，因此5V支路应预留至少3A并在模块附近增加电容。所有信号共地，但舵机电流不得
通过鲁班猫板载3.3V/5V引脚供给。

首次标定不假设通用的500～2500µs就是安全范围。先用保守脉宽和小角度移动，测出机械
边界，再把安全范围写入YAML。

## 8. 故障与安全

- 相机超时：停止跟踪，保持短时间后回中。
- I²C写入失败：停止继续更新，发布故障，不循环高速重试。
- 检测节点退出：控制节点因观测超时进入安全状态。
- 参数非法：节点拒绝激活，例如最小角度大于最大角度。
- 系统启动：默认待命，必须显式启用跟踪。
- 节点退出：尽力发送中位命令，但安全不能只依赖析构函数。

## 9. 后续升级

首版验收后再依次加入双轴云台、相机标定、人体检测、RKNN/NPU、网页监控和多目标策略。

## 10. 实施分层

系统设计使用阶段P0-P7表达能力边界，实际实施使用M00-M22半小时任务卡。阶段不能直接作为
执行任务，避免一次同时处理环境、视觉、控制和硬件。任务卡状态、顺序和验收产物以
[项目进度](03_progress_status.md)为准，执行与留痕规则以
[半小时执行手册](08_execution_playbook.md)为准。
