# LubanVision 快速入门

## 1. 当前设备与网络

| 设备 | 地址 | 角色 |
|---|---|---|
| MacBook M2 | `192.168.2.110` | 主仓、文档、SSH和项目管理 |
| Windows / WSL2 | `liu@192.168.2.100:2222` | ROS 2开发、RViz和数据分析 |
| 鲁班猫5 RK3588 | `root@192.168.2.120:22` | 相机、视觉、云台控制和部署 |

认证信息不得写入仓库。Windows必须先启动WSL2和其中的`sshd`。

```bash
python3 tools/network_check.py 192.168.2.100 192.168.2.120
ssh -p 2222 liu@192.168.2.100
ssh root@192.168.2.120
```

M17真实单轴验收使用仓库内的ID 23标记
[`assets/markers/aruco_4x4_50_id23.png`](../assets/markers/aruco_4x4_50_id23.png)。将相机安装为
画面水平轴与Pan转轴一致，确保云台附近无手、线缆和障碍物；在鲁班猫仓库根目录以root执行：

```bash
scripts/m17_live_acceptance.sh 20 30
```

脚本先等待连续5帧识别成功，随后才显式启用20秒跟踪；结束或异常退出都会请求禁用、停止
本次精确进程组并检查PWM清理。第三个可选参数可指定持久证据目录。

WSL的Linux用户固定为`liu`；不要使用Mac用户名`evanliu`。Mac公钥位于默认
`~/.ssh/id_ed25519`，已安装到`/home/liu/.ssh/authorized_keys`。如果端口可连接但公钥被
拒绝，先核对远端用户名，再检查WSL中的`sshd`和`authorized_keys`权限。

WSL和RK统一使用：

```bash
export ROS_DOMAIN_ID=20
```

项目GitHub远端固定为
[`lc285800/rk3588-camera-robot`](https://github.com/lc285800/rk3588-camera-robot)。
提交前必须先运行`git status -sb`和`git remote -v`核对范围与目标；完整提交、首次配置
`origin`和推送流程见[半小时执行手册](08_execution_playbook.md#8-git提交与推送)。

如果WSL看不到RK话题，优先检查Windows防火墙和WSL mirrored networking；不要通过关闭
全部防火墙或关闭TLS校验解决网络问题。

## 2. 系统选择

鲁班猫5使用与实际板卡版本完全匹配的野火Ubuntu 22.04 Server ARM64镜像：

- LubanCat-5只能使用`lubancat-5`镜像。
- LubanCat-5-V2只能使用`lubancat-5-v2`镜像。
- 4GB内存不安装GNOME、RViz和完整桌面。
- RViz、图像观察和rosbag分析放在Windows/WSL。

RK端已验证可安全安装的基础依赖：

```bash
sudo apt update
sudo apt install -y ros-humble-ros-base ros-dev-tools python3-rosdep \
  ros-humble-image-transport ros-humble-camera-info-manager \
  python3-opencv python3-smbus i2c-tools v4l-utils
```

不要在当前Rockchip镜像上直接安装`ros-humble-v4l2-camera`或`ros-humble-cv-bridge`。
Rockchip多媒体PPA的FFmpeg运行库带`+rkmpp`后缀，与Ubuntu标准开发包的精确版本依赖冲突。
当前M06验收使用项目内的`lubanvision_camera_cpp/v4l2_camera_publisher`直接读取V4L2 YUYV
并发布ROS图像消息，不降级板卡多媒体栈。Python版`lubanvision_vision/camera_publisher`保留
作低频调试样例。完整过程见[RK安装记录](07_rk_ros2_install.md)。

WSL端保留已经安装的`ros-humble-desktop`，具体记录见
[WSL2安装文档](06_wsl_ros2_install.md)。

软件闭环可以在WSL或RK复现，不需要连接舵机：

```bash
source /opt/ros/humble/setup.bash
cd ~/lubanvision/ros2_ws
source install/setup.bash
ros2 run lubanvision_control simulation_probe --output-dir /tmp/m14-check
```

期望正负阶跃均输出约`rise=1.850s`、`settle=2.750s`、`overshoot=0.000%`和
`steady=0.002169`。正式CSV、JSON和曲线位于
`artifacts/20260716/M14-simulated-gimbal/data/`。

## 3. 最小硬件

现有：

- 鲁班猫5 RK3588，4GB RAM和64GB存储。
- USB摄像头。
- 一个SG90舵机。

建议新增：

- 独立5V稳压电源或降压模块，额定电流需覆盖舵机启动和堵转需求。
- 舵机云台支架；双轴阶段再增加一个SG90。
- 杜邦线、端子和1000µF左右电解电容。
- 打印的ArUco标记。

首版使用物理Pin 32的`GPIO4_B6 / PWM13_M1`输出3.3V PWM信号。SG90电源接稳定的独立5V，
舵机电源负极必须与鲁班猫GND共地。禁止从GPIO或鲁班猫3.3V引脚给SG90供电，也不要带电改线。

## 4. 第一阶段：只验证相机

在RK上检查：

```bash
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video1 --list-formats-ext
ls -l /dev/video*
```

当前设备分配为：`/dev/video0`是板载HDMI RX，USB摄像头使用`/dev/video1`采集，
`/dev/video2`是同一USB设备的第二个接口。已确认USB摄像头原生支持640×480 MJPEG和
YUYV 30 FPS。

构建并启动项目相机节点：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=20
cd /root/lubanvision/ros2_ws
colcon build --symlink-install --packages-select lubanvision_camera_cpp lubanvision_vision
source install/setup.bash
ros2 run lubanvision_camera_cpp v4l2_camera_publisher --ros-args \
  -p video_device:=/dev/video1 \
  -p image_width:=640 \
  -p image_height:=480 \
  -p frame_rate:=15.0 \
  -p reliability:=reliable
```

在WSL中确认：

```bash
export ROS_DOMAIN_ID=20
ros2 topic list
ros2 topic hz /camera/image_raw
rviz2
```

在RK本机做短时频率探针：

```bash
ros2 run lubanvision_camera_cpp image_rate_probe --ros-args \
  -p topic:=/camera/image_raw \
  -p duration_sec:=15.0 \
  -p expected_width:=640 \
  -p expected_height:=480 \
  -p expected_encoding:=bgr8 \
  -p reliability:=reliable
```

相机稳定运行30分钟后，才能进入视觉识别。

## 5. 第二阶段：ArUco软件闭环

在不连接舵机时完成：

1. 相机节点发布图像。
2. 检测节点发布标记ID、中心坐标和`visible`状态。
3.控制节点将水平像素误差转换为目标角度。
4.使用模拟云台节点回报虚拟角度。
5.记录误差随时间收敛曲线。

软件闭环通过后再接SG90和独立5V电源，避免把图像、控制和接线问题混在一起。

## 6. 第三阶段：SoC PWM与SG90

物理Pin 32的PWM13_M1设备树复用已启用。无外设软件检查：

```bash
cat /sys/kernel/debug/pwm
grep 'pin 142 ' \
  /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins
```

已验证`pwmchip3/pwm0`可配置为20,000,000 ns周期（50Hz）和1,500,000 ns中位脉宽。
第一次舵机测试：

- 拆下云台负载或确保机械空间充足。
- 红线使用独立5V，负极与鲁班猫GND共地，信号线接物理Pin 32。
- 先发1.5 ms中位，再分别发1.45 ms和1.55 ms。
- 测量5V电源启动压降，确认RK没有重启。

未完成限位测试前，不运行自动扫描。

## 7. 正式启动流程

正式系统启动必须按以下顺序：

1. 相机和PWM设备自检。
2. 云台回到安全中位。
3. 启动检测节点。
4. 启动控制节点，但默认`tracking_enabled=false`。
5. 人工确认图像和目标状态后启用跟踪。

systemd只能启动到待命状态，不能上电后立即自动扫动舵机。
