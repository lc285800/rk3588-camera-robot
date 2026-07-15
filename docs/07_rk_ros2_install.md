# RK3588 ROS 2 Humble安装与验证记录

执行日期：2026-07-08

## 1. 环境确认

通过SSH只读检查得到：

| 项目 | 实测结果 |
|---|---|
| 板卡 | Embedfire LubanCat-5 |
| 系统 | Ubuntu 22.04.5 LTS |
| 架构 | aarch64 |
| 内核 | 6.1.84 |
| CPU | 8核 |
| 内存 | 3.8 GiB，另有2 GiB Swap |
| 根分区 | 58 GiB，检查时可用50 GiB |
| 时区 | Asia/Shanghai，NTP已同步 |
| USB摄像头 | Realtek `0bda:5846` |

设备节点：`/dev/video0`是板载HDMI RX；USB摄像头提供`/dev/video1`、`/dev/video2`
和`/dev/media0`。

## 2. ROS软件源

系统最初没有ROS软件源。旧方式下载的Open Robotics密钥指纹虽与历史记录一致，但APT
报告`EXPKEYSIG F42ED6FBAB17C654`，说明密钥已经过期。

最终使用ROS官方`ros-infrastructure/ros-apt-source` 1.2.0的Jammy配置包：

```text
ros2-apt-source_1.2.0.jammy_all.deb
SHA-256: 767884cf4ed03116b9d64438930a832ed854147ae435279a7924dfdf60f94433
```

安装配置包后，APT的ROS签名验证恢复正常。该配置默认包含`deb deb-src`，源码索引在当前
网络下反复重试，因此把`/usr/share/ros-apt-source/ros2.sources`的类型收窄为`deb`，项目
目前只需要二进制包。

## 3. 网络与代理

直连`packages.ros.org`存在HTTPS证书主机名不匹配和下载不稳定。RK已配置APT按域名代理：

```text
/etc/apt/apt.conf.d/80-ros-clash-proxy
```

只有`packages.ros.org`走`http://192.168.2.110:7897`，中科大Ubuntu镜像保持直连。详细
配置、验证和删除方法见[rk3588_clash_proxy_ros.md](rk3588_clash_proxy_ros.md)。

代理实测解决了可达性问题，但剩余7.33 MB ROS小包仍用时8分54秒，平均13.7 KB/s。
因此该配置的主要价值是稳定访问，不应描述为确定的带宽加速。

## 4. 已安装组件

以下组合安装成功：

```bash
apt-get install -y \
  ros-humble-ros-base ros-dev-tools python3-rosdep \
  ros-humble-image-transport ros-humble-camera-info-manager \
  python3-opencv python3-smbus i2c-tools v4l-utils
```

随后在加载Shell代理后完成：

```bash
source /usr/local/bin/proxy-on
rosdep init
rosdep update --rosdistro humble
```

验证结果：`ROS_DISTRO=humble`，`rclpy`、`image_transport`、`colcon`和`rosdep`均可用，
`dpkg --audit`无输出。

## 5. ROS基础验证

RK本机使用`ROS_DOMAIN_ID=20`发布字符串话题：

```bash
ros2 topic pub -r 5 /lubanvision/health std_msgs/msg/String \
  '{data: rk_ros_ok}'
```

另一个进程执行`ros2 topic echo --once /lubanvision/health`，实测收到：

```text
data: rk_ros_ok
```

这只证明RK本机DDS正常；WSL与RK的跨机DDS仍需单独验收。

## 6. 摄像头验证

`/dev/video1`支持：

- MJPEG：1280x720、640x480等分辨率，30 FPS。
- YUYV：640x480为30 FPS，1280x720为10 FPS。

执行900帧原始采集：

```bash
v4l2-ctl -d /dev/video1 \
  --set-fmt-video=width=640,height=480,pixelformat=MJPG \
  --set-parm=30 --stream-mmap=4 --stream-count=900 --stream-to=/dev/null
```

结果为31秒完成，稳定约29.95 FPS，启动阶段记录1个dropped buffer。该结果证明V4L2和
摄像头可用，但尚未满足ROS图像连续发布30分钟的V3完成条件。

## 7. 相机驱动依赖冲突

不能直接安装`ros-humble-v4l2-camera`或`ros-humble-cv-bridge`。它们间接要求Ubuntu标准
FFmpeg开发包的精确版本，而板卡Rockchip multimedia PPA已提供带`+rkmpp`后缀的运行库。
APT因此拒绝解析`libavcodec-dev`、`libavutil-dev`、`libswscale-dev`等依赖。

项目不通过强制降级解决，以免破坏RK硬件多媒体环境。最初实现
`lubanvision_vision/camera_publisher`，使用Python OpenCV读取V4L2并直接构造
`sensor_msgs/Image`；M06实测发现Python raw图像消息构造约6.9 FPS，不足以满足15 FPS目标。
当前M06验收路径改为`lubanvision_camera_cpp/v4l2_camera_publisher`：直接使用V4L2 YUYV采集，
C++内转换为`bgr8`并发布标准ROS图像消息，不依赖OpenCV开发包或`cv_bridge`。

## 8. 当前代码与测试状态

- `lubanvision_vision` 0.1.0已在RK完成`colcon build`。
- `lubanvision_camera_cpp` 0.1.0已在RK完成`colcon build`。
- `colcon test`正确发现3项Python静态测试，版权、Flake8和PEP257全部通过。
- 测试结果为3项、0错误、0失败、0跳过；Flake8仅输出依赖包元数据接口弃用警告。
- ROS图像话题的尺寸、短时帧率和稳定性预跑已验证；跨机DDS图像查看尚未验证。

M06冒烟测试已确认`/camera/image_raw`为640x480、`bgr8`、步长1920。最终验收命令使用
`lubanvision_camera_cpp/v4l2_camera_publisher`和`lubanvision_camera_cpp/image_rate_probe`，
参数为15 FPS、reliable QoS。两轮短测接收端分别为15.06 FPS和15.09 FPS，`bad_frames=0`。

2026-07-15完成M09：`lubanvision_interfaces`已在RK aarch64 ROS 2 Humble环境构建成功，
接口展开和Python消息构造断言通过。下一次唯一任务：M10 实现离线ArUco检测。

2026-07-09网络对照显示ROS HTTP包直连`packages.ros.org`比通过Mac Clash代理更快且更稳定；
RK的`/etc/apt/apt.conf.d/80-ros-clash-proxy`已改为默认直连，并保留备份
`80-ros-clash-proxy.bak-20260709-direct`。随后成功安装`ros-humble-rmw-cyclonedds-cpp`用于
对照；Cyclone对当前raw图像接收没有改善，最终M06采用Fast DDS + reliable QoS。

M07首次运行已启动但按用户要求提前暂停。暂停前C++发布器稳定输出15 FPS，最后记录到
`total=11700`、`missed=0`；资源采样显示相机CPU约17.1%、内存约0.6%，探针CPU约1.1%、
内存约0.5%，板温约37.0-38.8 C。2026-07-09用户确认该结果视为M07通过。

M08首次验证未通过。RK本地发布`/camera/image_raw`正常，ROS自带Fast DDS discovery server
在RK本机配合`ROS_SUPER_CLIENT=True`可发现话题；WSL侧同样设置仍不可见。WSL实际Linux接口
为`172.30.122.43/20`，当前`192.168.2.100:2222`是Windows侧SSH入口。WSL到RK的UDP测试包未
到达RK监听端口，因此跨机DDS图像验证需先处理WSL2 NAT/UDP网络。

2026-07-10通过Windows SSH继续排查。WSL恢复NAT后私网IP为`172.30.127.238`，Windows
portproxy已更新到该地址并恢复Mac到WSL的SSH。Windows本机能访问WSL私网SSH，但RK经Windows
路由仍无法访问WSL私网；Windows接口Forwarding、`IPEnableRouter=1`和RemoteAccess已启用，
可能需要Windows重启后验证。

2026-07-10 M08复测通过。WSL到RK的UDP `nc`探测可到达RK监听端口；RK运行ROS自带Fast DDS
Discovery Server `192.168.2.120:11811`，并以`ROS_DOMAIN_ID=20`、
`ROS_DISCOVERY_SERVER=192.168.2.120:11811`发布`/camera/image_raw`。WSL设置相同domain和
discovery server，并开启`ROS_SUPER_CLIENT=True`后，`ros2 topic list -t`可见
`/camera/image_raw [sensor_msgs/msg/Image]`，`ros2 topic echo --once`读取到`640x480 bgr8`
图像样本，`ros2 topic hz`短测约15 Hz。M08按该定向发现方案通过；默认multicast和RK主动访问
WSL私网仍不作为当前可用能力。
