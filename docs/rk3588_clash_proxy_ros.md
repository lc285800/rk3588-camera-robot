# RK3588 通过 MacBook Clash 加速 ROS 下载

本文记录 RK3588 板卡通过 MacBook 上的 Clash 代理访问外网，并针对 ROS 软件源进行代理加速的完整配置和验证过程。

## 目标配置

- 配置日期：`2026-07-08`
- 板卡：RK3588 / LubanCat
- 板卡系统：Ubuntu 22.04.5 LTS，ARM64
- 板卡 SSH 地址：`192.168.2.120`
- 板卡 SSH 用户：`root`
- MacBook 局域网地址：`192.168.2.110`
- Clash HTTP 代理端口：`7897`
- ROS 发行版：ROS 2 Humble
- ROS 软件源：`http://packages.ros.org/ros2/ubuntu`
- Ubuntu ARM64 镜像：中科大 `mirrors.ustc.edu.cn`

配置目标：

- `packages.ros.org` 单独通过 MacBook Clash 访问。
- 中科大 Ubuntu ARM64 镜像保持直连，避免国内流量绕行代理。
- 提供 shell 级别的代理开启、关闭脚本，用于 GitHub、`curl` 等工具。

## 1. 网络拓扑

本次检查到的实际地址如下：

| 设备 | 接口/用途 | 地址 |
| --- | --- | --- |
| MacBook | 小米 15 热点网络 | `10.213.252.157` |
| MacBook | 与板卡互通的局域网接口 | `192.168.2.110` |
| RK3588 | 小米 15 热点，`wlan0` | `10.213.252.123` |
| RK3588 | SSH/局域网地址 | `192.168.2.120` |

板卡访问代理时使用：

```text
http://192.168.2.110:7897
```

> MacBook 必须保持开机并运行 Clash。Clash 需要开启“允许局域网连接”，且 macOS 防火墙不能拦截 `7897` 端口。

## 2. 确认 MacBook 地址和 Clash 监听状态

在 MacBook 上执行：

```bash
route -n get default
ifconfig
lsof -nP -iTCP:7897 -sTCP:LISTEN
```

本次检查结果：

```text
MacBook 局域网地址：192.168.2.110
Clash：TCP *:7897 (LISTEN)
```

`*:7897` 表示 Clash 不只监听本机回环地址，局域网设备可以连接。

## 3. 确认板卡与代理端口连通

在 MacBook 上确认板卡 SSH 可达：

```bash
nc -vz -w 3 192.168.2.120 22
```

确认 Clash 端口正在监听：

```bash
nc -vz -w 3 192.168.2.110 7897
```

两个端口本次均连接成功。

登录板卡：

```bash
ssh root@192.168.2.120
```

## 4. 验证 Clash 代理出口

在板卡上分别测试 Cloudflare、Google 和 GitHub：

```bash
curl -x http://192.168.2.110:7897 \
  -sS --connect-timeout 5 --max-time 12 \
  -o /dev/null \
  -w 'HTTP %{http_code}, connect %{time_connect}s, total %{time_total}s\n' \
  http://cp.cloudflare.com/generate_204

curl -x http://192.168.2.110:7897 \
  -sS --connect-timeout 5 --max-time 12 \
  -o /dev/null \
  -w 'HTTP %{http_code}, connect %{time_connect}s, total %{time_total}s\n' \
  https://www.google.com/generate_204

curl -x http://192.168.2.110:7897 \
  -sS --connect-timeout 5 --max-time 12 \
  -o /dev/null \
  -w 'HTTP %{http_code}, connect %{time_connect}s, total %{time_total}s\n' \
  https://raw.githubusercontent.com/ros/rosdistro/master/ros.key
```

本次结果：

```text
Cloudflare：HTTP 204，约 0.69 秒
Google：HTTP 204，约 0.60 秒
GitHub：HTTP 200，约 0.80 秒
```

说明板卡到 MacBook 的代理链路以及 Clash 的外网出口均正常。

## 5. 验证 ROS 软件源

板卡实际配置的 ROS 源为 HTTP：

```text
URIs: http://packages.ros.org/ros2/ubuntu
```

通过 Clash 测试：

```bash
curl -x http://192.168.2.110:7897 \
  -sS --connect-timeout 5 --max-time 20 \
  -o /dev/null \
  -w 'HTTP %{http_code}, total %{time_total}s\n' \
  http://packages.ros.org/ros2/ubuntu/dists/jammy/InRelease
```

本次返回：

```text
HTTP 200，约 5.88 秒
```

直连 ROS HTTPS 地址时曾出现证书主机名不匹配，而通过 Clash 访问其他 HTTPS 站点正常。因此采用按域名代理的方式，绕过异常的 ROS 直连链路。

## 6. 配置 APT 按域名代理

在板卡上创建：

```text
/etc/apt/apt.conf.d/80-ros-clash-proxy
```

文件内容：

```text
Acquire::http::Proxy "DIRECT";
Acquire::https::Proxy "DIRECT";
Acquire::http::Proxy::packages.ros.org "http://192.168.2.110:7897";
Acquire::https::Proxy::packages.ros.org "http://192.168.2.110:7897";
```

含义：

- APT 默认直连。
- 只有 `packages.ros.org` 通过 Clash。
- `mirrors.ustc.edu.cn` 等国内源继续直连。

检查 APT 是否已经读取配置：

```bash
apt-config dump | grep -A5 -B2 -F 'packages.ros.org'
```

后续新启动的 `apt-get update` 和 `apt-get install` 会自动使用该配置。

## 7. 配置临时全局代理开关

板卡上已创建以下两个脚本：

```text
/usr/local/bin/proxy-on
/usr/local/bin/proxy-off
```

开启当前 shell 的代理：

```bash
source /usr/local/bin/proxy-on
```

关闭当前 shell 的代理：

```bash
source /usr/local/bin/proxy-off
```

必须使用 `source` 或前导点加载脚本：

```bash
. /usr/local/bin/proxy-on
```

如果直接执行 `proxy-on`，环境变量只会作用于脚本自己的子进程，不能修改当前 shell。

开启后设置的主要环境变量包括：

```text
http_proxy=http://192.168.2.110:7897
https_proxy=http://192.168.2.110:7897
HTTP_PROXY=http://192.168.2.110:7897
HTTPS_PROXY=http://192.168.2.110:7897
ALL_PROXY=http://192.168.2.110:7897
```

局域网地址和中科大镜像加入了 `no_proxy`，保持直连。

## 8. 最终验证

开启 shell 代理后执行：

```bash
source /usr/local/bin/proxy-on

curl -sS --max-time 10 \
  -o /dev/null \
  -w 'GitHub via shell proxy: HTTP %{http_code}, %{time_total}s\n' \
  https://raw.githubusercontent.com/ros/rosdistro/master/ros.key
```

本次最终结果：

```text
GitHub via shell proxy: HTTP 200, 0.592254s
```

检查时 ROS 2 Humble 安装任务仍在运行：

```text
apt-get install -y ros-humble-ros-base ros-dev-tools ...
```

## 9. 常见问题

### 代理端口可连接，但外网请求失败

检查 Clash 是否开启“允许局域网连接”，并确认当前节点可用：

```bash
curl -x http://192.168.2.110:7897 \
  --connect-timeout 5 --max-time 10 \
  https://www.google.com/generate_204
```

### MacBook 的地址发生变化

重新在 MacBook 上执行 `ifconfig` 查找与板卡同网段的地址，然后同时修改：

```text
/etc/apt/apt.conf.d/80-ros-clash-proxy
/usr/local/bin/proxy-on
```

### APT 仍未使用新配置

APT 进程只在启动时读取配置。已经运行中的 `apt-get` 不会动态切换代理，需要等待当前任务结束，再重新启动相应命令。

### 国内 Ubuntu 镜像速度反而下降

确认 APT 默认配置仍为 `DIRECT`，不要把所有 APT 流量都强制送入代理：

```bash
apt-config dump | grep -i proxy
```

## 10. 删除配置

不再需要该代理时执行：

```bash
rm -f /etc/apt/apt.conf.d/80-ros-clash-proxy
rm -f /usr/local/bin/proxy-on /usr/local/bin/proxy-off
```

删除后重新启动 APT 命令即可恢复默认网络行为。
