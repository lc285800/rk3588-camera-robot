# 问题记录

问题编号使用`ISSUE-YYYYMMDD-NN`。每项记录环境、现象、复现、日志、根因、修复和回归
结果；密码、Wi-Fi密钥和私有令牌不得写入。

## 模板

- 编号、状态、日期：
- 环境：Mac、WSL或RK；系统、内核、ROS 2版本、代码提交：
- 现象与期望：
- 最小复现：
- 日志、截图或rosbag：
- 已排除项：
- 根因：
- 修复：
- 回归验证：
- 预防措施：

## 当前问题

### ISSUE-20260702-01：Mac不承担ROS 2 Humble目标构建

- 状态：已决策。
- 说明：MacBook M2负责主仓、文档和SSH；Windows/WSL2负责桌面开发，RK负责ARM64运行。
- 影响：Mac缺少colcon不是项目阻塞项。

### ISSUE-20260708-02：RK3588镜像与板卡版本待确认

- 状态：已解决。
- 风险：LubanCat-5与LubanCat-5-V2镜像、设备树不能混用。
- 验证：记录背面丝印、镜像完整名称、`uname -a`和`cat /etc/os-release`。
- 结果：设备树确认为`Embedfire LubanCat-5`，系统为Ubuntu 22.04.5 LTS ARM64，内核
  `6.1.84`；内存、存储和时间同步正常。

### ISSUE-20260708-03：WSL与RK跨机DDS待验证

- 状态：待测试。
- 方案：首先使用同网段multicast；失败时检查Windows防火墙和mirrored networking，再
  考虑Fast DDS discovery server。禁止直接关闭全部防火墙。

### ISSUE-20260708-04：PCA9685总线和舵机安全范围未知

- 状态：待硬件到位。
- 风险：选错I²C总线、逻辑电平或PWM范围可能导致无响应、抖动或撞限位。
- 方案：先`i2cdetect`，再使用70°～110°保守范围，小步测试并记录安全脉宽。

### ISSUE-20260708-05：Rockchip FFmpeg包阻塞ROS相机驱动安装

- 状态：修复待回归。
- 环境：LubanCat-5，Ubuntu 22.04.5 ARM64，Rockchip multimedia PPA，ROS 2 Humble。
- 现象：安装`ros-humble-v4l2-camera`或`ros-humble-cv-bridge`时，Ubuntu标准
  `libavcodec-dev`、`libavutil-dev`等要求精确版本，但板卡已安装带`+rkmpp`后缀的运行库。
- 已排除：ROS基础环境、V4L2设备和摄像头本身正常；640x480 MJPEG 30 FPS原始采集通过。
- 约束：不得直接强制降级或删除Rockchip多媒体运行库，以免破坏板卡硬件编解码环境。
- 当前方案：已建立`lubanvision_vision/camera_publisher`，使用Python OpenCV读取V4L2并
  直接构造`sensor_msgs/Image`，不依赖`cv_bridge`。
- 待验证：ROS图像话题和30分钟稳定性通过后，才能确认该绕行方案可关闭此问题。

### ISSUE-20260708-06：ROS旧签名密钥过期

- 状态：已解决。
- 现象：使用旧`ros.key`执行`apt update`返回`EXPKEYSIG F42ED6FBAB17C654`。
- 根因：项目旧文档记录的Open Robotics签名密钥已经过期。
- 修复：从ROS官方`ros-infrastructure/ros-apt-source` 1.2.0发布获取
  `ros2-apt-source_1.2.0.jammy_all.deb`，核对SHA-256后安装，由配置包管理新密钥和软件源。
- 回归：ROS软件源`InRelease`签名通过，`ros-humble-ros-base`安装完成。
- 预防：不再手工复制长期固定的`ros.key`；优先使用官方`ros2-apt-source`配置包。

### ISSUE-20260708-07：ROS软件源下载慢且直连HTTPS异常

- 状态：已缓解。
- 现象：RK直连`packages.ros.org`时HTTPS证书主机名不匹配，HTTP下载大量小包速度慢。
- 修复：仅将`packages.ros.org`转发到MacBook Clash `7897`端口，中科大Ubuntu镜像保持直连。
- 实测：代理连通和HTTP 200正常；剩余7.33 MB ROS包用时8分54秒，平均13.7 KB/s。
- 结论：代理提高可用性和稳定性，但本次未表现出明显吞吐加速；大量小包约4秒一次请求是
  主要耗时。配置和删除方法见`docs/rk3588_clash_proxy_ros.md`。

### ISSUE-20260708-08：ROS包版权测试失败

- 状态：已解决。
- 环境：RK ROS 2 Humble，`lubanvision_vision` 0.1.0。
- 现象：`colcon test`发现3项测试，Flake8和PEP257通过，`ament_copyright`报告许可证未知。
- 根因：Humble的`ament_copyright`不识别简写`Licensed under the Apache License, Version 2.0`。
- 修复：本地5个Python文件已替换为完整Apache 2.0标准版权头。
- 回归：清理该包构建与安装缓存后重新构建，3项测试全部通过，0错误、0失败、0跳过。

### ISSUE-20260708-09：Python ROS原始图像发布性能不足

- 状态：已解决，保留Python节点但M06验收改用C++节点。
- 现象：M06消息尺寸和编码正确，但默认可靠QoS下`ros2 topic hz`短时只观察到约0.46 Hz。
- 对照：同一摄像头由Python OpenCV连续读取120帧，实测27.82 FPS，排除V4L2采集瓶颈。
- 根因：640x480 BGR图像约0.88 MiB；RK上Python给`sensor_msgs/Image.data`赋值921600字节时
  仅约6.9 msg/s，构造raw图像消息本身已低于15 FPS目标。Best Effort和Cyclone DDS不能解决
  该发布端瓶颈。
- 修复：新增`lubanvision_camera_cpp`，直接使用V4L2 YUYV采集，C++内转换为`bgr8`并发布标准
  `sensor_msgs/Image`；发布器和探针支持`reliability`参数，M06使用reliable QoS验收。
- 回归现状：发布者实际QoS确认为`BEST_EFFORT/VOLATILE`；`topic echo --qos-profile
  sensor_data`能够收到640高的图像，但收到前报告丢失2条。轻量Python订阅计数器首次得到
  0帧，测试脚本又因未启用`pipefail`误返回成功，结果无效。
- 修复补充：2026-07-09已新增`image_rate_probe`作为包内订阅计数探针；相机节点新增
  `stats_interval_sec`发布端计数日志。
- 回归：`lubanvision_camera_cpp`在RK构建通过；C++发布器以640x480、`bgr8`、15 FPS、reliable
  QoS运行两轮短测，发布端稳定15 FPS，C++探针接收端分别为15.06 FPS和15.09 FPS，
  `bad_frames=0`，SIGINT退出正常。
- 预防措施：后续高带宽raw图像链路优先使用C++节点；Python节点可保留作低频调试或接口样例。

### ISSUE-20260708-10：相机节点退出时重复关闭ROS上下文

- 状态：已解决。
- 现象：测试发送SIGINT或timeout后，`rclpy.shutdown()`报告`rcl_shutdown already called`。
- 根因：信号处理已关闭上下文，`finally`再次无条件调用shutdown。
- 修复：只在`rclpy.ok()`为真时调用`rclpy.shutdown()`。
- 回归：同步RK后使用SIGINT退出，要求进程无Python traceback。
- 2026-07-09回归：使用`timeout -s INT`结束相机节点，日志未出现Python traceback或
  `rcl_shutdown already called`。

### ISSUE-20260709-11：WSL2 NAT阻塞默认跨机DDS图像发现

- 状态：已绕过，M08通过；默认multicast和RK主动访问WSL私网仍不可用。
- 环境：RK `192.168.2.120/24`，WSL Linux接口`172.30.122.43/20`，Windows/SSH入口
  `192.168.2.100:2222`，ROS_DOMAIN_ID=20。
- 现象：RK发布`/camera/image_raw`正常，RK本机可通过Fast DDS discovery server发现该话题；
  WSL无法通过默认multicast或`ROS_DISCOVERY_SERVER=192.168.2.120:11811`发现该话题。
- 最小复现：RK启动`v4l2_camera_publisher`；WSL执行`ros2 topic list`仅看到`/parameter_events`
  和`/rosout`。RK启动ROS自带Fast DDS discovery server后，RK本机配合`ROS_SUPER_CLIENT=True`
  可见`/camera/image_raw`，WSL仍不可见。
- 网络证据：WSL可ping RK且可TCP连接RK SSH 22。2026-07-09首次`nc -u`探测未到达；2026-07-10
  WSL重启并恢复portproxy后，WSL到RK UDP探测可到达RK监听端口。RK经Windows路由访问WSL私网
  `172.30.127.238`仍失败。
- 根因判断：当前WSL2 NAT网络不提供ROS 2 DDS所需的UDP/multicast可达性；`192.168.2.100`
  是Windows侧地址，不是WSL Linux参与DDS的接口地址。
- 解决：M08采用RK侧Fast DDS Discovery Server `192.168.2.120:11811`。RK相机发布器和WSL订阅
  端统一设置`ROS_DOMAIN_ID=20`、`ROS_DISCOVERY_SERVER=192.168.2.120:11811`；WSL额外设置
  `ROS_SUPER_CLIENT=True`。该方案下WSL可发现`/camera/image_raw`，可读取`640x480 bgr8`
  图像样本，`ros2 topic hz`短测约15 Hz。
- 后续：不要依赖默认multicast发现；不要直接关闭全部Windows防火墙。若将来需要RK主动连接WSL
  私网服务，再处理Windows路由或迁移到支持mirrored networking的环境。
- 2026-07-10补充：Windows 10 Home环境未验证到可用mirrored networking。删除`.wslconfig`后
  WSL私网IP变更导致`2222`端口转发失效，已更新portproxy到`172.30.127.238:22`并恢复SSH。
  尝试启用Windows三层转发：`以太网`和`vEthernet (WSL)`接口Forwarding已开启，
  `IPEnableRouter=1`已写入注册表，RemoteAccess服务已启动；RK添加
  `172.30.112.0/20 via 192.168.2.100`后仍无法访问WSL私网。当前M08不再等待Windows重启，
  后续如需双向三层互访，再重启Windows验证路由开关或改用不依赖WSL2 NAT的网络/桥接方案。

### ISSUE-20260715-12：M11独立进程发现和图像QoS不稳定

- 状态：已解决，保留Discovery Server启动等待约束。
- 环境：RK ROS 2 Humble/Fast DDS，M11 ArUco节点，640x480 BGR图像。
- 现象：默认发现、`ROS_LOCALHOST_ONLY=1`以及双方都设`ROS_SUPER_CLIENT=True`时，独立探针
  发布82帧而检测节点收到0帧；Best Effort订阅真实Reliable相机时接收间歇，约4至5 FPS。
- 无效尝试：在加载ROS环境前启用`set -u`导致`AMENT_TRACE_SETUP_FILES`未定义；停止
  `ros2 run`外层PID未结束实际节点；两项均已在后续脚本修正并保留失败记录。
- 根因：该网络必须沿用M08的Fast DDS角色配置；发布端是普通Discovery Server客户端，检测
  订阅端设为SUPER_CLIENT。图像QoS必须与M06的Reliable发布路径一致。
- 修复：节点图像订阅改为Reliable/Volatile；按Server、SUPER_CLIENT检测节点、普通相机发布
  端顺序启动并等待发现。停止时先停相机，后停检测节点；捕获`ExternalShutdownException`。
- 回归：真实相机发布225帧保持15 FPS；发现完成后检测节点每2秒稳定增加30帧，输入错误0，
  无标记场景误检0。确定性同executor集成用于字段和时间戳验证，61条观测错误0。
- 预防：M11后续启动文件固化DDS角色和Reliable QoS；性能窗口忽略发现建立前的累计时间。

### ISSUE-20260716-13：macOS tar元数据干扰RK Python lint

- 状态：已解决。
- 环境：Mac向RK同步新`lubanvision_control`包，RK ROS 2 Humble。
- 现象：首次tar同步生成`._setup.py`等AppleDouble文件，导致copyright、Flake8和PEP257
  读取到非UTF-8内容或空字节。
- 根因：macOS文件扩展属性随归档生成AppleDouble伴随文件，非项目源码问题。
- 修复：远端同步后删除`._*`，清理该包build/install缓存后重新构建测试。
- 回归：本包16项测试全部通过，0失败。
- 预防：从macOS向Linux归档同步源码时禁用扩展属性，并在验收前检查和删除`._*`。

### ISSUE-20260716-14：WSL SSH误用Mac本地用户名

- 状态：已解决。
- 环境：Mac连接Windows端口转发`192.168.2.100:2222`进入WSL Ubuntu 22.04。
- 现象：TCP端口和SSH协议均正常，但使用`evanliu@192.168.2.100:2222`时公钥认证被拒绝。
- 已排除：Windows主机在线、2222端口可达、WSL `sshd`为active、远端主机密钥未变化。
- 根因：WSL Linux账号是`liu`，`evanliu`是Mac本地账号；公钥安装在
  `/home/liu/.ssh/authorized_keys`，错误账号下自然无法匹配。
- 修复：恢复使用`ssh -p 2222 liu@192.168.2.100`。
- 回归：BatchMode免密登录成功；主机`DESKTOP-KSDDPU2`、ROS 2 Humble和colcon均可用。
- 预防：快速入门固定记录三机用户名；认证失败时先核对目标用户，再检查密钥和端口转发。

### ISSUE-20260716-15：模拟闭环积分与死区形成低幅极限环

- 状态：已解决，硬件参数仍需M16-M17重新标定。
- 环境：M14归一化单轴模拟云台，`dt=0.05 s`，一阶舵机时间常数`0.18 s`。
- 现象：首轮参数`Kp=1.8`、`Ki=0.12`、`Kd=0.08`、死区`0.005`时，正负阶跃上升时间
  1.55秒、超调3.63%，但8秒内未进入2%稳定带；末段误差在约0.017附近持续摆动。
- 根因：积分在死区外继续积累，进入死区后输出回零；一阶执行器惯性将误差推过中心，随后
  积分反向释放，形成对称低幅极限环。
- 修复：M14验收参数改为保守PD：`Kp=1.5`、`Ki=0`、`Kd=0.12`、死区`0.003`，保留输出
  和周期增量限幅。
- 回归：正负阶跃均1.85秒达到90%响应、2.75秒进入2%稳定带、0%超调、稳态误差0.002169。
- 预防：软件模拟参数不得直接作为硬件参数；真实SG90接入后从PD开始，小步增加积分并监测
  死区附近振荡。
