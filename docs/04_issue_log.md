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

- 状态：待检查。
- 风险：LubanCat-5与LubanCat-5-V2镜像、设备树不能混用。
- 验证：记录背面丝印、镜像完整名称、`uname -a`和`cat /etc/os-release`。

### ISSUE-20260708-03：WSL与RK跨机DDS待验证

- 状态：待测试。
- 方案：首先使用同网段multicast；失败时检查Windows防火墙和mirrored networking，再
  考虑Fast DDS discovery server。禁止直接关闭全部防火墙。

### ISSUE-20260708-04：PCA9685总线和舵机安全范围未知

- 状态：待硬件到位。
- 风险：选错I²C总线、逻辑电平或PWM范围可能导致无响应、抖动或撞限位。
- 方案：先`i2cdetect`，再使用70°～110°保守范围，小步测试并记录安全脉宽。
