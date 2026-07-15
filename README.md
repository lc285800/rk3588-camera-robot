# LubanVision：RK3588 ROS 2 视觉跟踪云台机器人

LubanVision 是一个以 Linux、ROS 2 和主动视觉为主线的机器人学习项目。鲁班猫5
（RK3588，4GB RAM）读取 USB 摄像头图像，ROS 2 节点识别 ArUco 标记并计算画面误差，
通过 Linux I²C 控制 PCA9685，驱动 SG90 云台持续将目标保持在画面中心。

首版不依赖AI模型。所有核心环境、代码、日志和故障都可以通过SSH直接分析与修复，
优先保证项目完整落地。

## 系统分工

```text
MacBook M2（项目控制台）
  Git / 文档 / 任务管理 / SSH 运维
                 │ 家庭局域网
Windows + WSL2（开发工作站） ───── 鲁班猫5 RK3588（机器人运行端）
  ROS 2编译、RViz、rosbag分析          USB摄像头
                                      │ 图像
                              ArUco识别 + PID控制
                                      │ I²C
                                   PCA9685
                                      │ PWM
                                1～2个SG90云台
```

Mac和Windows断开后，机器人仍能在鲁班猫5上独立运行。第一阶段使用单轴水平跟踪；验证稳定
后增加第二个SG90，升级为水平和俯仰双轴跟踪。

## 首版交付能力

- USB摄像头ROS 2驱动与远程图像查看。
- OpenCV ArUco检测、目标中心和置信状态发布。
- 可测试的PID视觉伺服控制器。
- PCA9685 Linux I²C驱动和SG90安全角度控制。
- 目标丢失后的保持、回中和有限扫描状态机。
- 摄像头、I²C或节点异常时停止更新舵机，禁止无限旋转或撞限位。
- YAML参数、rosbag记录、systemd开机待命和结构化日志。
- 后续可选的人体检测、RK3588 NPU推理和网页监控。

## 仓库状态

仓库只保留LubanVision相关内容。`lubanvision_vision`提供离线ArUco检测和ROS目标观测节点；
`lubanvision_camera_cpp`提供M06验收使用的低开销V4L2相机发布和速率探针，不依赖
`cv_bridge`或OpenCV开发包。`lubanvision_interfaces`提供目标观测消息；控制、硬件、描述和
bringup包按半小时任务卡逐步建立。

## 文档

- [快速入门](docs/01_quick_start.md)
- [系统设计](docs/02_design.md)
- [项目进展](docs/03_progress_status.md)
- [问题记录](docs/04_issue_log.md)
- [测试计划](docs/05_test_plan.md)
- [WSL2 ROS 2安装记录](docs/06_wsl_ros2_install.md)
- [RK3588 ROS 2安装与验证记录](docs/07_rk_ros2_install.md)
- [RK3588 Clash代理与ROS下载记录](docs/rk3588_clash_proxy_ros.md)
- [半小时任务执行手册](docs/08_execution_playbook.md)
