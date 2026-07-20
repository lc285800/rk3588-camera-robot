# 项目进展与状态

最后更新：2026-07-20

## 1. 当前结论

项目完成**阶段P4：软件闭环**，进入**阶段P5：单轴硬件**。M00-M14均已完成；基础架构、
三机环境、ROS摄像头、ArUco视觉、PID、目标丢失状态机和模拟云台闭环均已通过。M15的
PWM软件预检和真实SG90小步硬件冒烟已经通过；当前只等待把12V 1.5A临时输入升级为可靠的
12V 3A，或改用独立稳压5V舵机电源。供电复测通过前不进入M16。M14正负阶跃在Mac、WSL
和RK产生完全一致的数据：1.85秒达到90%响应，2.75秒进入2%稳定带，0%超调，稳态归一化
误差约0.00217。

## 2. 阶段视图

| 阶段 | 范围 | 状态 | 完成条件 |
|---|---|---|---|
| P0 项目定义 | M00 | 已完成 | 架构、接口、测试路线和Git基线齐全 |
| P1 三机环境 | M01-M04 | 已完成 | WSL与RK基础环境、ROS和V4L2可用 |
| P2 ROS摄像头 | M05-M08 | 已完成 | RK稳定发布图像，WSL可跨机查看 |
| P3 ArUco视觉 | M09-M11 | 已完成 | 离线和ROS流均发布正确目标观测 |
| P4 软件闭环 | M12-M14 | 已完成 | PID、丢失状态机和模拟云台通过 |
| P5 单轴硬件 | M15-M18 | 进行中 | 单轴安全跟踪及故障注入通过 |
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
| M12 | 实现可测试PID核心 | 已完成 | 方向、死区、积分和限速单元测试 |
| M13 | 实现目标丢失状态机 | 已完成 | 跟踪、保持、回中状态测试 |
| M14 | 建立模拟云台闭环 | 已完成 | 阶跃收敛曲线和控制指标 |
| M15 | 盘点SoC PWM与供电 | 进行中 | PWM复用、50Hz输出、电压和接线记录 |
| M16 | 完成SG90保守标定 | 未开始 | 85/90/95度动作及安全范围YAML |
| M17 | 完成单轴视觉闭环 | 未开始 | ArUco单轴跟踪视频和误差统计 |
| M18 | 完成硬件故障注入 | 未开始 | 相机/PWM/节点异常安全状态记录 |
| M19 | 建立bringup与systemd | 未开始 | 开机待命、人工启用和结构化日志 |
| M20 | 完成首版系统验收 | 未开始 | 60分钟运行、rosbag及验收报告 |
| M21 | 扩展双轴跟踪 | 未开始 | Tilt标定、TF和双轴跟踪结果 |
| M22 | 整理作品集 | 未开始 | 架构、曲线、视频、问题复盘和说明 |

## 4. 当前任务卡

**当前唯一任务：M15 盘点SoC PWM与供电。**

- 当前状态：PWM设备树复用、50Hz周期、1.5ms中位脉宽和安全关闭的软件测试已通过。
  2026-07-20真实SG90短时执行1.50/1.45/1.50/1.55/1.50ms小步序列，用户确认轻微转动，
  RK未重启且摄像头、NVMe、网线保持在线。当前12V 1.5A输入低于官方12V 2A规格，SG90又
  暂用板载共享5V，因此只视为硬件冒烟通过，等待升级供电后完成M15。
- 2026-07-20新增`lubanvision_hardware`受限sysfs PWM核心：默认禁用，只允许1.45-1.55ms
  临时冒烟范围，拒绝接管已有消费者，异常时禁用并取消导出。WSL与RK硬件包各23项测试、
  全工作区各67项测试全部通过；本次离线验证未导出RK真实PWM，不改变M15供电阻塞状态。
- 输入：鲁班猫5物理Pin 32、`GPIO4_B6 / PWM13_M1`、SG90，以及满足裕量要求的板卡或舵机
  供电方案。
- 下一步操作：将板卡输入升级为可靠的12V 3A，或让SG90使用独立稳压5V 2A以上电源并共地；
  随后重复中位和小步动作，确认供电稳定后完成M15。
- 完成：确认PWM13_M1、50Hz输出、供电额定值、共地和接线记录，并在最终供电条件下重复
  中位及小步动作且RK和主要外设保持在线。
- 失败：电压不明、无法共地或PWM输出异常时保持进行中，不进入M16动作标定。
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
- 2026-07-16 M12完成：新增ROS无关的`lubanvision_control`包和单轴PID核心；明确正图像
  X误差默认产生负Pan增量，死区不积分，积分限幅默认0表示禁用积分，输出绝对值和每周期增量
  分别限幅。RK Humble构建成功，本包16项测试全部通过；证据位于
  `artifacts/20260716/M12-pid-core/`。
- 2026-07-16 M13完成：新增ROS无关的目标丢失状态机，目标可见时跟踪，丢失后先保持，
  到达超时边界后回中，默认不存在扫描状态；首次捕获和丢失后重新捕获均请求清理PID历史。
  WSL与RK的控制包各27项测试全部通过；证据位于
  `artifacts/20260716/M13-target-loss-state/`。
- 2026-07-16三机连接复核：WSL正确入口为`liu@192.168.2.100:2222`，Mac公钥免密登录、
  WSL `sshd`、ROS 2 Humble和colcon均正常；此前认证失败是误用Mac用户名`evanliu`，不是
  密钥或端口转发故障。RK免密SSH和`/dev/video1`摄像头同时在线。
- 2026-07-16 M14完成：新增确定性单轴云台模拟器和`simulation_probe`。正负0.6归一化
  误差阶跃均在1.85秒达到90%响应、2.75秒进入2%稳定带、0%超调，稳态误差0.002169；
  最大输出0.5、最大周期变化0.08均符合限幅。WSL与RK控制包各33项测试通过，工作区各44项
  测试0失败；Mac、WSL、RK生成的CSV、JSON和SVG哈希完全一致。证据位于
  `artifacts/20260716/M14-simulated-gimbal/`。
- 2026-07-17 M15软件预检通过：首版硬件路线由PCA9685调整为RK3588 SoC PWM直驱单轴。
  物理Pin 32对应`GPIO4_B6`、编号142和`PWM13_M1`；设备树插件加载后新增
  `pwmchip3 -> febf0010.pwm`。在无外设条件下成功配置50 Hz、1.5 ms中位脉宽，内核确认
  Pin 142切换到`pwm13m1-pins`；测试后已关闭并取消导出。M15仍等待独立5V供电和接线核对，
  证据位于`artifacts/20260717/M15-soc-pwm-inventory/`。
- 2026-07-20 M15硬件冒烟有限通过：SG90在1.45-1.55ms保守范围内产生轻微转动，RK及主要
  外设未掉线，PWM安全关闭。受12V 1.5A输入和板载共享5V限制，M15仍进行中；证据位于
  `artifacts/20260720/M15-servo-smoke/`。
- 2026-07-20 M15安全控制准备通过：新增受限sysfs PWM核心和20项功能测试，双端含lint共
  23项通过，全工作区各67项测试通过。YAML范围明确标为临时冒烟值；证据位于
  `artifacts/20260720/M15-safe-pwm-core/`。

## 6. 更新纪律

每完成或中断一张任务卡，必须记录：开始状态、执行命令、关键输出、日志位置、测试编号、
问题编号、代码提交和下一张唯一任务。详细格式见
[半小时执行手册](08_execution_playbook.md)。
