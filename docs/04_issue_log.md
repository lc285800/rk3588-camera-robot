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

- 状态：处理中。
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

- 状态：待回归。
- 环境：RK ROS 2 Humble，`lubanvision_vision` 0.1.0。
- 现象：`colcon test`发现3项测试，Flake8和PEP257通过，`ament_copyright`报告许可证未知。
- 根因：Humble的`ament_copyright`不识别简写`Licensed under the Apache License, Version 2.0`。
- 修复：本地5个Python文件已替换为完整Apache 2.0标准版权头。
- 下一步：同步到RK后清理该包测试结果并执行`colcon test-result --verbose`。
