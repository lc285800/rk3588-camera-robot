# 项目进展与状态

最后更新：2026-07-15

## 1. 当前结论

项目完成**阶段P3：ArUco视觉**，进入**阶段P4：软件闭环**。基础架构、WSL环境、
RK系统和ROS 2 Humble已经落地；USB摄像头的V4L2能力已验证。M06 ROS图像冒烟测试已通过；
M07稳定性预跑在用户主动暂停前持续十几分钟正常，按用户验收口径视为通过。M08通过Fast DDS
Discovery Server定向发现方案完成：WSL可发现并订阅RK发布的`/camera/image_raw`。

## 2. 阶段视图

| 阶段 | 范围 | 状态 | 完成条件 |
|---|---|---|---|
| P0 项目定义 | M00 | 已完成 | 架构、接口、测试路线和Git基线齐全 |
| P1 三机环境 | M01-M04 | 已完成 | WSL与RK基础环境、ROS和V4L2可用 |
| P2 ROS摄像头 | M05-M08 | 已完成 | RK稳定发布图像，WSL可跨机查看 |
| P3 ArUco视觉 | M09-M11 | 已完成 | 离线和ROS流均发布正确目标观测 |
| P4 软件闭环 | M12-M14 | 进行中 | PID、丢失状态机和模拟云台通过 |
| P5 单轴硬件 | M15-M18 | 未开始 | 单轴安全跟踪及故障注入通过 |
| P6 部署验收 | M19-M20 | 未开始 | 开机待命和60分钟稳定运行通过 |
| P7 扩展交付 | M21-M22 | 未开始 | 双轴可选升级和作品集材料完成 |

## 3. 半小时里程碑

每个里程碑只允许一个主要目标，设计工作量约为一次30分钟模型执行。外部下载、硬件采购、
30/60分钟稳定运行不计为模型工作时间，但必须在对应任务中启动、监控并记录结果。

| ID | 目标 | 状态 | 验收产物 |
|---|---|---|---|
| M00 | 建立项目基线 | 已完成 | Git、设计、测试计划和问题日志 |
| M01 | 验证WSL ROS 2本机环境 | 已完成 | Humble发布订阅与RViz可用记录 |
| M02 | 盘点RK板卡与系统 | 已完成 | 板卡、镜像、内核、资源和时间同步记录 |
| M03 | 安装并验证RK ROS 2 | 已完成 | ros-base、colcon、rosdep及本机DDS通过 |
| M04 | 枚举USB摄像头 | 已完成 | `/dev/video1`格式表及900帧采集结果 |
| M05 | 建立视觉包与测试基线 | 已完成 | 构建通过且3项静态测试全部通过 |
| M06 | 发布ROS图像并冒烟测试 | 已完成 | 640x480图像、话题频率和样本字段正确 |
| M07 | 完成摄像头稳定性测试 | 已完成 | 30分钟日志、FPS、丢帧、CPU和内存统计 |
| M08 | 验证WSL与RK跨机图像 | 已完成 | WSL订阅话题并在RViz显示图像 |
| M09 | 定义目标观测接口 | 已完成 | `lubanvision_interfaces`构建和消息测试 |
| M10 | 实现离线ArUco检测 | 已完成 | 静态样本正例、反例和遮挡测试 |
| M11 | 接入ROS ArUco节点 | 已完成 | 观测、调试图、时间戳和性能统计 |
| M12 | 实现可测试PID核心 | 未开始 | 方向、死区、积分和限速单元测试 |
| M13 | 实现目标丢失状态机 | 未开始 | 跟踪、保持、回中状态测试 |
| M14 | 建立模拟云台闭环 | 未开始 | 阶跃收敛曲线和控制指标 |
| M15 | 盘点PCA9685与供电 | 未开始 | I2C总线、地址、电压和接线记录 |
| M16 | 完成SG90保守标定 | 未开始 | 85/90/95度动作及安全范围YAML |
| M17 | 完成单轴视觉闭环 | 未开始 | ArUco单轴跟踪视频和误差统计 |
| M18 | 完成硬件故障注入 | 未开始 | 相机/I2C/节点异常安全状态记录 |
| M19 | 建立bringup与systemd | 未开始 | 开机待命、人工启用和结构化日志 |
| M20 | 完成首版系统验收 | 未开始 | 60分钟运行、rosbag及验收报告 |
| M21 | 扩展双轴跟踪 | 未开始 | Tilt标定、TF和双轴跟踪结果 |
| M22 | 整理作品集 | 未开始 | 架构、曲线、视频、问题复盘和说明 |

## 4. 当前任务卡

**当前唯一任务：M12 实现可测试PID核心。**

- 输入：M11的`TargetObservation`输出、单轴Pan控制方向和安全限速需求。
- 操作：实现不依赖ROS的PID核心，覆盖方向、死区、积分抗饱和、输出和每周期增量限幅。
- 完成：方向、死区、积分上限、输出限幅和非法输入单元测试通过。
- 失败：记录控制符号或限幅语义争议，不进入M13目标丢失状态机。
- 文档：更新本文件、测试计划和问题日志。
- 2026-07-09恢复点：M06最终使用`lubanvision_camera_cpp/v4l2_camera_publisher`和
  `lubanvision_camera_cpp/image_rate_probe`完成；Python raw图像路径因消息数组赋值约6.9 FPS
  不再作为M06验收路径。
- 2026-07-09 M08现状：RK本地相机发布正常；RK本机通过Fast DDS discovery server和
  `ROS_SUPER_CLIENT=True`可发现`/camera/image_raw`；WSL仍无法发现该话题。WSL Linux接口为
  `172.30.122.43/20`，不是文档中的Windows侧`192.168.2.100`；WSL到RK的UDP测试未到达RK监听
  端口，需启用WSL mirrored networking或提供UDP可达的DDS通道后继续。
- 2026-07-10修复尝试：删除`.wslconfig`后WSL私网IP变为`172.30.127.238`，已修复Windows
  `2222`端口转发。Windows本机可访问WSL私网SSH，但RK经`192.168.2.100`路由到
  `172.30.127.238`仍不通；已启用Windows接口Forwarding、`IPEnableRouter=1`和RemoteAccess，
  可能需要Windows重启后才能生效。
- 2026-07-10 M08通过：重新验证WSL到RK的UDP `nc`探测可到达；RK启动Fast DDS Discovery
  Server `192.168.2.120:11811`并发布`/camera/image_raw`，WSL设置`ROS_DOMAIN_ID=20`、
  `ROS_DISCOVERY_SERVER=192.168.2.120:11811`和`ROS_SUPER_CLIENT=True`后可发现话题、
  `ros2 topic echo --once`读取到`640x480 bgr8`样本，`ros2 topic hz`短测稳定约15 Hz。
  RK主动访问WSL私网仍不通，该限制保留为网络约束，不阻塞M09。

## 5. 已完成事实

- RK确认为Embedfire LubanCat-5，Ubuntu 22.04.5 ARM64，内核6.1.84。
- RK具有3.8 GiB内存、58 GiB根分区，NTP时间同步和SSH正常。
- ROS 2 Humble、colcon、rosdep、V4L2和I2C工具可用，本机DDS收到`rk_ros_ok`。
- USB摄像头使用`/dev/video1`，640x480 MJPEG/YUYV均支持30 FPS。
- V4L2完成900帧、31秒采集，稳定约29.95 FPS，启动时丢弃1个缓冲区。
- `lubanvision_vision`已在RK构建；版权、Flake8和PEP257共3项测试全部通过。
- `lubanvision_camera_cpp`已建立并在RK构建通过，使用V4L2 YUYV采集并转换为`bgr8`发布。
- Python `sensor_msgs/Image.data`赋值921600字节时约6.9 msg/s，不能满足15 FPS raw图像发布。
- 2026-07-09从Mac确认`192.168.2.100`和`192.168.2.120`可ping通，WSL SSH `2222`与RK SSH
  `22`端口开放；已将Mac的SSH公钥安装到WSL和RK，BatchMode免密登录通过。
- `config/platforms/lubancat5.yaml`的相机设备已修正为实测USB摄像头`/dev/video1`。
- RK端`colcon test --packages-select lubanvision_vision lubanvision_camera_cpp`通过；
  `colcon test-result`为3项测试、0错误、0失败、0跳过。
- M06最终验收：C++发布器以640x480、`bgr8`、15 FPS、reliable QoS运行两轮短测，发布端均为
  15.00 FPS左右，接收端分别为224帧/14.87秒=15.06 FPS、225帧/14.91秒=15.09 FPS，
  `bad_frames=0`，SIGINT退出正常。
- M07首次稳定性测试已启动但按用户要求暂停；暂停前记录到`total=11700`帧、
  所有30秒窗口均为450帧约15.00 FPS、`missed=0`。资源采样显示相机CPU约17.1%、内存约0.6%，
  探针CPU约1.1%、内存约0.5%，板温约37.0-38.8 C。用户确认该预跑结果可视为M07通过。
- M08最终验收：WSL2 NAT下默认multicast不可用，但通过RK侧Fast DDS Discovery Server
  `192.168.2.120:11811`和WSL侧`ROS_SUPER_CLIENT=True`完成跨机发现与订阅；WSL读取到
  `640x480 bgr8`图像样本，频率短测约15 Hz。Windows 10 Home当前未提供可用mirrored
  networking，RK主动访问WSL私网仍不可用。
- 2026-07-15 M09完成：新增`lubanvision_interfaces/msg/TargetObservation`，明确图像时间戳、
  目标ID、中心坐标、像素/归一化误差、面积、置信度和检测状态。WSL amd64与RK arm64均构建
  成功，`ros2 interface show`及Python消息构造断言通过。证据位于
  `artifacts/20260715/M09-target-observation-interface/`。
- 2026-07-15 M10完成：新增与ROS传输解耦的`aruco_detector`，使用固定生成的640x480静态
  图像验证目标ID、四角点、像素/归一化误差、空白图、非目标ID、50%遮挡及非法输入。
  WSL与RK各8项测试全部通过；两端与本地主仓关键文件SHA-256一致。证据位于
  `artifacts/20260715/M10-offline-aruco/`。
- 2026-07-15 M11完成：ROS节点逐帧发布目标观测并默认每15帧发布调试图；确定性ROS集成
  验证61条观测、4张调试图、源时间戳和字段错误0。真实C++相机链路在Reliable QoS下发现后
  稳定处理15 FPS，无标记场景检测数0；RK采样约77% CPU、4.1%内存、RSS约168 MB，包含调试
  图开销的P95约162 ms。证据位于`artifacts/20260715/M11-ros-aruco/`。

## 6. 更新纪律

每完成或中断一张任务卡，必须记录：开始状态、执行命令、关键输出、日志位置、测试编号、
问题编号、代码提交和下一张唯一任务。详细格式见
[半小时执行手册](08_execution_playbook.md)。
