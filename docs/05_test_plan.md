# LubanVision 测试计划

原则：先离线、再ROS 2；先模拟、再硬件；先单轴、再双轴。任何电源、PWM或机械限位问题
未解决前，不运行自动跟踪。

测试按[项目进度](03_progress_status.md)中的M00-M22任务卡执行。一个任务卡可以覆盖多个
测试的准备工作，但只有记录实际结果后才能修改测试状态。

## 1. 环境和网络

- T-ENV-01：RK确认Ubuntu 22.04 Server ARM64、4GB内存、可用存储和时间同步。
- T-NET-01：Mac分别SSH到WSL和RK，连续连接稳定。
- T-NET-02：RK发布测试话题，WSL在`ROS_DOMAIN_ID=20`下可以订阅。
- T-BUILD-01：WSL amd64和RK arm64均完成新ROS 2包构建与测试。

## 2. 摄像头

- T-CAM-01：记录`v4l2-ctl --list-formats-ext`，只选择摄像头原生格式。
- T-CAM-02：640×480、15 FPS持续发布30分钟，无节点退出和持续丢帧。
- T-CAM-03：拔掉摄像头后节点给出明确故障；重新插入后的恢复方式有文档。该故障注入属于
  M18，不作为M04-M08摄像头基础链路完成的前置条件。
- T-CAM-04：WSL/RViz可查看图像，网络中断不导致RK视觉进程失控。

## 3. ArUco检测

- T-VIS-01：静态图片中正确识别目标ID和四个角点。
- T-VIS-02：非目标ID、无标记和部分遮挡不会产生有效目标观测；运动模糊下的连续控制安全性
  在真实硬件闭环M17-M18验证。
- T-VIS-03：发布的中心坐标、归一化误差和时间戳正确。
- T-VIS-04：录制rosbag回放时检测结果可重复。该端到端回放项归入M19-M20系统验收，不作为
  M09-M11视觉节点完成的前置条件。
- T-VIS-05：在RK上测量CPU、内存、平均FPS和95百分位处理延迟。

## 4. 控制器和模拟云台

- T-CTL-01：正误差产生正确方向的Pan调整，防止左右方向接反。
- T-CTL-02：死区内不连续更新，积分有上限，输出角度和每周期增量受限。
- T-CTL-03：目标丢失后依次进入保持和回中，默认不自动扫描。
- T-CTL-04：旧时间戳、非法数值和错误目标ID不会驱动云台。
- T-CTL-05：模拟云台下阶跃误差稳定收敛，记录上升时间、超调和稳态误差。

## 5. SoC PWM与舵机

- T-PWR-01：舵机独立5V电源空载和启动电压合格，动作时RK不重启。
- T-PWM-01：PWM13_M1设备树复用正确，50Hz周期和中位脉宽可配置并安全关闭。
- T-SERVO-01：无负载时完成90°、85°、95°小步动作，方向与命令一致。
- T-SERVO-02：测出安全脉宽和机械角度范围，写入YAML后不能越界。
- T-SERVO-03：快速连续命令被速率限制，不产生明显撞击和过热。
- T-SERVO-04：PWM配置或节点异常时停止更新并发布故障，不进行无限高速重试。

## 6. 系统验收

- T-END-01：移动ArUco目标时单轴云台持续将其保持在画面中心附近。
- T-END-02：目标丢失、摄像头拔出、检测节点退出、PWM异常时进入定义的安全状态。
- T-END-03：systemd开机只进入待命，不自动转动，人工启用后才能跟踪。
- T-END-04：连续运行60分钟，记录温度、CPU、内存、FPS、误差和故障数。
- T-END-05：rosbag包含图像、目标观测、云台命令、状态和诊断，可在WSL离线复现。
- T-END-06：完成架构讲解、正常跟踪、目标丢失和故障注入的连续演示视频。

双轴、人体检测和NPU均不属于首版通过条件。

## 7. 执行记录

| 测试 | 日期 | 状态 | 结果 |
|---|---|---|---|
| T-ENV-01 | 2026-07-08 | 通过 | LubanCat-5，Ubuntu 22.04.5 ARM64，3.8 GiB内存，时间同步正常 |
| T-NET-01 | 2026-07-08 | 部分通过 | Mac到WSL和RK网络可达；RK SSH登录正常，WSL SSH需单独复核认证 |
| T-NET-01复核 | 2026-07-09 | 通过 | Mac可ping通`192.168.2.100`和`192.168.2.120`，WSL `2222`与RK `22`端口开放；SSH公钥免密登录WSL和RK通过 |
| T-NET-02 | 2026-07-10 | 通过 | WSL2 NAT下默认multicast不可用；改用RK侧Fast DDS Discovery Server `192.168.2.120:11811`后，WSL可发现并订阅RK `/camera/image_raw` |
| T-BUILD-01 | 2026-07-15 | 通过 | M09接口包在WSL amd64与RK arm64均构建成功；接口展开和Python消息构造断言通过 |
| T-CAM-01 | 2026-07-08 | 通过 | `/dev/video1`原生支持640x480 MJPEG/YUYV 30 FPS |
| T-CAM-02 | 2026-07-09 | 通过 | V4L2原始采集31秒、900帧通过；ROS 15 FPS冒烟通过；M07稳定性预跑暂停前正常，按用户验收口径通过 |
| T-CAM-02冒烟 | 2026-07-09 | 通过 | C++ V4L2发布器640x480 `bgr8`、15 FPS、reliable QoS两轮短测通过，接收端15.06/15.09 FPS，异常帧0 |
| T-CAM-02稳定性预跑 | 2026-07-09 | 通过 | M07测试按用户要求提前暂停；暂停前发布端记录到11700帧，30秒窗口均为450帧约15.00 FPS，`missed=0`，资源和温度稳定，用户确认视为通过 |
| T-CAM-04/M08预检 | 2026-07-10 | 通过 | RK发布图像正常；WSL经Fast DDS Discovery Server发现`/camera/image_raw`，读取到`640x480 bgr8`样本，短测频率约15 Hz |
| T-VIS-01 | 2026-07-15 | 通过 | 生成式静态样本正确识别目标ID 23、四角点、中心、面积和误差方向；WSL/RK回归通过 |
| T-VIS-02/M09-M11范围 | 2026-07-15 | 通过 | 无标记、非目标ID和50%遮挡均无有效观测；真实无标记相机流误检0。运动模糊下的硬件连续控制归入M17-M18 |
| T-VIS-03 | 2026-07-15 | 通过 | ROS集成61条观测与4张调试图字段正确，源sec/nanosec/frame_id保持且序号不重复 |
| T-VIS-04 | - | M19-M20计划项 | rosbag端到端回放归入系统验收，不阻塞已完成的M09-M11视觉阶段 |
| T-VIS-05 | 2026-07-15 | 通过 | 真实相机发现后稳定处理15 FPS；约77% CPU、4.1%内存、RSS 168 MB、P95约162 ms |
| T-CTL-01 | 2026-07-16 | 通过 | PID默认方向为负：正归一化X误差产生负Pan增量，正负方向测试通过 |
| T-CTL-02 | 2026-07-16 | 通过 | 死区、双向积分限幅、绝对输出限幅和每周期增量限幅测试通过 |
| T-CTL-04/PID输入 | 2026-07-16 | 通过 | NaN/Inf误差以及零、负数、NaN/Inf时间步均被明确拒绝 |
| T-CTL-03 | 2026-07-16 | 通过 | 目标丢失后先保持，在超时边界进入回中；重新捕获请求清PID，默认无扫描状态 |
| T-CTL-04/状态输入 | 2026-07-16 | 通过 | 非布尔可见状态、非法时间和时间倒退均被明确拒绝 |
| T-CTL-05 | 2026-07-16 | 通过 | 正负0.6阶跃均1.85秒达到90%响应、2.75秒进入2%稳定带、0%超调、稳态误差0.002169 |
| T-PWM-01/软件预检 | 2026-07-17 | 通过 | Pin 32的PWM13_M1加载为pwmchip3；无外设下50Hz/1.5ms输出、Pin 142复用和关闭清理通过 |
| M15/SG90硬件冒烟 | 2026-07-20 | 有限通过 | 1.45-1.55ms小步序列产生轻微转动，RK及主要外设未掉线；12V 1.5A输入与共享5V不满足正式供电验收，M15保持进行中 |
| T-PWM-01/安全核心 | 2026-07-20 | 通过 | 默认禁用、临时脉宽硬限位、已有消费者拒绝、异常/超时清理共20项功能测试通过；双端含lint各23项、全工作区各67项0失败，未导出真实PWM |
| T-SERVO-01/M16第1轮 | 2026-07-20 | 有限通过 | 正式安全核心完成1.45/1.50/1.55ms真实三点复验，RK及外设正常；方向已确认，85/90/95度仍为名义映射而非机械实测 |
| T-SERVO-01/1.45ms方向复验 | 2026-07-20 | 通过 | 用户重复观察确认1.45ms从中位向左，恢复1.50ms时向右回中并停止；系统健康且PWM已清理 |
| T-SERVO-01/1.55ms方向复验 | 2026-07-20 | 通过 | 用户确认1.55ms从中位向右，恢复1.50ms时向左回中并停止；系统健康且PWM已清理 |
| T-SERVO-02/临时三点映射 | 2026-07-20 | 有限通过 | 85/90/95度名义值映射到1.45/1.50/1.55ms，方向与PWM双重限位测试通过；WSL/RK硬件包各38项、全工作区各82项0失败，仍待可靠供电下实际量角和边界测试 |
| T-CTL-04/M17观测门控 | 2026-07-21 | 通过 | 错误目标、过期/未来时间戳、非法值不驱动；新鲜ID 23观测才进入跟踪，新增8项控制测试通过 |
| T-SERVO-03/M17合成闭环 | 2026-07-21 | 通过 | 143条状态覆盖tracking/holding/returning/disabled，PWM为1,463,998-1,500,000ns，故障0，默认禁用和结束清理均通过 |
| T-END-01/M17真实链预检 | 2026-07-21 | 部分通过 | 真实相机与ArUco连续处理900帧约15 FPS、错误0；当前画面ID 23检测0，待标记入镜后完成动态跟踪视频和误差统计 |
| T-END-01/M17安全门控 | 2026-07-21 | 通过 | 无标记时连续5帧门控在3秒超时后失败关闭，舵机未启用、运行进程无残留、PWM未导出；正式20秒动态验收待相机朝向调整和标记入镜 |
| T-SERVO-02/M16扩展目测 | 2026-07-21 | 有限通过 | 手持短时观察确认1.00ms约0度、1.90ms约90度、2.50ms约150度；均停止在固定位置并可返回，确认非360度连续旋转型。未实测到180度，待量角器和长期供电验收 |
| T-CTL-01/M17硬件方向A/B | 2026-07-21 | 通过 | 静止标记下`direction=+1`使误差0.590增至0.754；`direction=-1`使误差0.185降至0.035（约81%），91帧持续检测、故障0，正确方向固定为`-1` |

临时远端日志曾写入`/tmp/lubanvision_build.log`、`/tmp/lubanvision_test.log`、
`/tmp/lubanvision_camera.log`和`/tmp/lubanvision_ros_pub.log`。`/tmp`不是持久日志目录，正式
30分钟测试必须把日志和统计写入项目约定的持久目录。

M06持久产物位于RK：`/root/lubanvision/artifacts/20260708/M06-camera-smoke/`。第一次尝试因
`pkill -f`误匹配父命令而退出；第二次确认消息结构；QoS对照结果见`rate.txt`、
`sensor-qos-rate.txt`和`logs/`。轻量订阅计数器因管道返回码处理错误，0帧结果只作为无效
尝试保留，不作为性能结论。

2026-07-09本地新增`image_rate_probe`，用于以传感器QoS轻量订阅`/camera/image_raw`并统计
帧数、FPS和异常尺寸/编码帧；相机节点新增`stats_interval_sec`发布端计数日志。Mac本地完成
Python编译检查和脚本语法检查；同步到RK后构建通过，3项静态测试全部通过。

RK短时ROS回归未通过：15 FPS时发布端约3.71-6.75 FPS，探针20秒收到5帧；5 FPS时发布端
稳定5 FPS，探针15秒收到2帧，40秒收到4帧。日志位于
`/root/lubanvision/artifacts/20260709/M06-camera-smoke/logs/`。当前判断需继续排查Fast DDS
raw图像传输或切换Cyclone DDS对照；Cyclone安装暂被RK的`unattended-upgrade`占用dpkg锁阻塞。

随后确认瓶颈在Python raw `Image.data`赋值，921600字节消息构造约6.9 msg/s。新增
`lubanvision_camera_cpp`，直接使用V4L2 YUYV采集并转换为`bgr8`，不依赖OpenCV开发包。
Fast DDS Best Effort接收存在随机丢帧；C++发布器和C++探针使用reliable QoS后，15 FPS两轮
短测通过：发布端稳定15 FPS，接收端分别为15.06 FPS和15.09 FPS，`bad_frames=0`。M06完成，
M07稳定性预跑按用户验收口径通过，继续M08跨机图像验证。

M07首次稳定性测试产物位于RK
`/root/lubanvision/artifacts/20260709/M07-camera-stability/`，本地摘要位于
`artifacts/20260709/M07-camera-stability/result.md`。本次按用户要求提前暂停；暂停前相机链路
正常，最后记录到11700帧、`missed=0`，CPU、内存和温度均稳定。2026-07-09用户确认该结果
视为M07通过。

M08首次验证产物位于`artifacts/20260709/M08-cross-machine-image/`。WSL当时Linux接口为
`172.30.122.43/20`，Windows侧`192.168.2.100:2222`只是SSH进入WSL的端口转发入口。RK本机
通过Fast DDS discovery server和`ROS_SUPER_CLIENT=True`可发现`/camera/image_raw`，但WSL
同样配置仍不可见；WSL到RK的UDP `nc`测试未到达RK监听端口。M08受阻，建议启用WSL mirrored
networking或建立真实UDP可达的DDS网络后重测。

2026-07-10进一步处理：Windows SSH已可用；删除`.wslconfig`后WSL回到NAT模式，私网IP变为
`172.30.127.238`，已修复Windows `2222`到WSL SSH的portproxy。尝试让Windows作为
`192.168.2.0/24`与`172.30.112.0/20`之间的路由器，已启用接口Forwarding、`IPEnableRouter=1`
和RemoteAccess服务，但RK仍无法访问WSL私网IP。当时判断若必须RK主动访问WSL私网，需要Windows
重启验证全局路由是否生效，或改用其他非WSL NAT方案。

2026-07-10复测通过：WSL到RK的UDP `nc`探测到达RK监听端口。RK启动Fast DDS Discovery Server
`192.168.2.120:11811`和C++相机发布器后，WSL设置`ROS_DOMAIN_ID=20`、
`ROS_DISCOVERY_SERVER=192.168.2.120:11811`、`ROS_SUPER_CLIENT=True`，`ros2 topic list -t`
可见`/camera/image_raw [sensor_msgs/msg/Image]`；`ros2 topic echo --once`读取到
`height=480`、`width=640`、`encoding=bgr8`；`ros2 topic hz`短测稳定约15 Hz。M08按该定向
发现方案通过。RK主动访问WSL私网仍不通，作为网络约束记录，不阻塞后续M09。

## 8. 任务映射

| 任务卡 | 主要测试 |
|---|---|
| M01-M03 | T-ENV-01、T-NET-01及RK本机DDS冒烟测试 |
| M04-M08 | T-CAM-01、T-CAM-02、T-CAM-04、T-NET-02、T-BUILD-01 |
| M09-M11 | T-VIS-01、T-VIS-02检测范围、T-VIS-03、T-VIS-05 |
| M12-M14 | T-CTL-01至T-CTL-05 |
| M15-M18 | T-PWR-01、T-PWM-01、T-SERVO-01至T-SERVO-04、T-CAM-03、T-VIS-02硬件连续控制范围 |
| M19-M20 | T-VIS-04、T-END-01至T-END-06 |

M21双轴扩展不属于首版通过条件；M22负责整理已有测试证据，不替代任何未执行测试。

M12证据位于`artifacts/20260716/M12-pid-core/`。RK ROS 2 Humble环境中
`lubanvision_control`构建成功，本包收集16项测试并全部通过；工作区汇总为27项测试、
0错误、0失败、0跳过。

M13证据位于`artifacts/20260716/M13-target-loss-state/`。WSL amd64与RK arm64均完成
`lubanvision_control`构建；每端本包27项测试全部通过，工作区汇总38项测试、0错误、
0失败、0跳过。

M14证据位于`artifacts/20260716/M14-simulated-gimbal/`。WSL amd64与RK arm64均完成
`lubanvision_control`构建；每端本包33项测试全部通过，工作区汇总44项测试、0错误、
0失败、0跳过。Mac、WSL和RK独立运行`simulation_probe`后，`metrics.json`、
`step_response.csv`和`step_response.svg`的SHA-256逐项一致。
