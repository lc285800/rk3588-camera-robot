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

WSL和RK统一使用：

```bash
export ROS_DOMAIN_ID=20
```

如果WSL看不到RK话题，优先检查Windows防火墙和WSL mirrored networking；不要通过关闭
全部防火墙或关闭TLS校验解决网络问题。

## 2. 系统选择

鲁班猫5使用与实际板卡版本完全匹配的野火Ubuntu 22.04 Server ARM64镜像：

- LubanCat-5只能使用`lubancat-5`镜像。
- LubanCat-5-V2只能使用`lubancat-5-v2`镜像。
- 4GB内存不安装GNOME、RViz和完整桌面。
- RViz、图像观察和rosbag分析放在Windows/WSL。

RK端基础依赖：

```bash
sudo apt update
sudo apt install -y ros-humble-ros-base ros-dev-tools python3-rosdep \
  ros-humble-v4l2-camera ros-humble-image-transport \
  ros-humble-cv-bridge ros-humble-camera-info-manager \
  python3-opencv python3-smbus i2c-tools v4l-utils
```

WSL端保留已经安装的`ros-humble-desktop`，具体记录见
[WSL2安装文档](06_wsl_ros2_install.md)。

## 3. 最小硬件

现有：

- 鲁班猫5 RK3588，4GB RAM和64GB存储。
- USB摄像头。
- 一个SG90舵机。

建议新增：

- PCA9685 16路PWM模块一块。
- 独立5V/3A稳压电源或降压模块。
- 舵机云台支架；双轴阶段再增加一个SG90。
- 杜邦线、端子和1000µF左右电解电容。
- 打印的ArUco标记。

PCA9685逻辑电源接3.3V，舵机电源接稳定5V，鲁班猫、PCA9685与舵机电源必须共地。
禁止从鲁班猫3.3V引脚给SG90供电，也不要在接入鲁班猫前带电改线。

## 4. 第一阶段：只验证相机

在RK上检查：

```bash
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
ls -l /dev/video*
```

先选择摄像头原生支持的640×480、15或30 FPS格式。启动ROS 2相机：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=20
ros2 run v4l2_camera v4l2_camera_node --ros-args \
  -p video_device:=/dev/video0 \
  -p image_size:="[640,480]" \
  -p time_per_frame:="[1,15]" \
  -p camera_frame_id:=camera_link
```

在WSL中确认：

```bash
export ROS_DOMAIN_ID=20
ros2 topic list
ros2 topic hz /image_raw
rviz2
```

相机稳定运行30分钟后，才能进入视觉识别。

## 5. 第二阶段：ArUco软件闭环

在不连接舵机时完成：

1. 相机节点发布图像。
2. 检测节点发布标记ID、中心坐标和`visible`状态。
3.控制节点将水平像素误差转换为目标角度。
4.使用模拟云台节点回报虚拟角度。
5.记录误差随时间收敛曲线。

软件闭环通过后再接PCA9685，避免把图像、控制和接线问题混在一起。

## 6. 第三阶段：PCA9685与SG90

在RK上确认I²C总线和设备树后执行：

```bash
i2cdetect -l
sudo i2cdetect -y <bus-number>
```

正常情况下能看到PCA9685默认地址`0x40`。第一次舵机测试：

- 拆下云台负载或确保机械空间充足。
- 角度限制暂设为70°～110°。
- 先发90°中位，再分别发85°和95°。
- 测量5V电源启动压降，确认RK没有重启。

未完成限位测试前，不运行自动扫描。

## 7. 正式启动流程

正式系统启动必须按以下顺序：

1. 相机和I²C设备自检。
2. 云台回到安全中位。
3. 启动检测节点。
4. 启动控制节点，但默认`tracking_enabled=false`。
5. 人工确认图像和目标状态后启用跟踪。

systemd只能启动到待命状态，不能上电后立即自动扫动舵机。
