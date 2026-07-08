# WSL2 ROS 2 Humble 安装记录

执行日期：2026-07-07  
记录日期：2026-07-08

## 1. 目标与环境

依据 `docs/01_quick_start.md`，Windows 开发机使用 WSL2 Ubuntu 22.04 和 ROS 2 Humble。
本次从 Mac 通过 SSH 管理 WSL，远端环境确认如下：

- SSH：`liu@192.168.2.100:2222`
- 系统：Ubuntu 22.04.5 LTS（Jammy）
- 架构：amd64
- ROS 2：Humble
- ROS 2 域：`ROS_DOMAIN_ID=20`

密码等认证信息不得写入仓库。

2026-07-08 从 MacBook `192.168.2.110` 重新实测局域网连接成功，远端主机名为
`DESKTOP-KSDDPU2`。此前使用的 `10.213.252.192` 是旧地址，不再作为当前连接入口。

## 2. 安装过程

先安装 locale、软件源和签名工具：

```bash
sudo apt update
sudo apt install -y locales software-properties-common curl gnupg2 ca-certificates
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
sudo add-apt-repository -y universe
sudo install -d -m 0755 /usr/share/keyrings
```

导入 Open Robotics 软件包签名密钥，并核对指纹：

```text
C1CF 6E31 E6BA DE88 68B1 72B4 F42E D6FB AB17 C654
```

配置Jammy软件源后安装ROS 2桌面开发环境：

```bash
sudo apt update
sudo apt install -y ros-humble-desktop ros-dev-tools python3-rosdep \
  ros-humble-v4l2-camera
```

安装完成时记录的软件包版本：

| 软件包 | 版本 |
|---|---|
| `ros-humble-desktop` | `0.10.0-1jammy.20260612.213429` |
| `ros-dev-tools` | `1.0.1` |
| `python3-rosdep` | `0.26.0-1` |
| `ros-humble-v4l2-camera` | `0.6.2-1jammy.20260606.044055` |

## 3. 验证结果

以下组件均能从 `/opt/ros/humble` 加载：

```bash
source /opt/ros/humble/setup.bash
ros2 pkg prefix rviz2
ros2 pkg prefix v4l2_camera
```

使用域 ID 20 启动示例发布者，并读取一次 `/chatter`：

```bash
export ROS_DOMAIN_ID=20
ros2 run demo_nodes_cpp talker
ros2 topic echo --once /chatter
```

实测收到：

```text
data: 'Hello World: 1'
```

结论：ROS 2 Humble本机发布/订阅、RViz、OpenCV开发基础和V4L2相机组件可用。

## 4. 遇到的问题

### SSH 端口有监听但没有协议响应

最初 TCP 端口 2222 可连接，但 SSH 在 banner exchange 阶段超时。启动 WSL Ubuntu 22.04
并恢复其中的 SSH 服务后连接正常。若再次出现，先在 Windows 检查 WSL 实例、`sshd` 和
端口转发目标，而不是反复尝试密码。

### GitHub 与 ROS 站点访问异常

- WSL 无法连接 `raw.githubusercontent.com`。
- `packages.ros.org` 的 HTTPS 连接曾返回证书域名不匹配。
- 没有使用 `curl -k` 或关闭 TLS 校验；签名密钥经可用的 GitHub HTTPS 地址获取，并核对
  Open Robotics 指纹后才导入。
- APT 使用软件包签名验证 ROS 仓库内容。

### rosdep 缓存尚未更新

`rosdep` 源目录和默认列表已建立，但 `rosdep update --rosdistro humble` 在读取 GitHub 数据时
超时，因此本地 rosdep 缓存尚未完成。ROS 2 二进制安装和发布/订阅验证不受影响；在网络
恢复后执行：

```bash
rosdep update --rosdistro humble
```

在 rosdep 更新成功前，执行 `scripts/build.sh` 可能在依赖解析阶段失败。

## 5. 日常使用

每个新终端先执行：

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=20
```

仓库同步到WSL、rosdep缓存更新成功并建立`lubanvision_*`软件包后，继续执行：

```bash
./scripts/test.sh
./scripts/build.sh
source ros2_ws/install/setup.bash
```
