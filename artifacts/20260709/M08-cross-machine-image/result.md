# M08 Cross-Machine Image Validation

## Status

Passed on 2026-07-10 using an RK-side Fast DDS Discovery Server.

## What Worked

- RK camera publisher ran normally at 640x480 `bgr8`, 15 FPS, reliable QoS.
- RK local Fast DDS discovery server worked when `ROS_SUPER_CLIENT=True` was set.
- RK local ROS CLI could discover `/camera/image_raw` through the discovery server.
- Mac to WSL and Mac to RK SSH remained available.
- WSL and RK could ping each other through the Windows host address path.
- WSL could open TCP to RK SSH port 22.
- On the final retry, WSL-to-RK UDP using `nc -u` reached the RK listener.
- WSL discovered `/camera/image_raw` through `ROS_DISCOVERY_SERVER=192.168.2.120:11811`.
- WSL read one `sensor_msgs/msg/Image` sample: `height=480`, `width=640`, `encoding=bgr8`.
- WSL `ros2 topic hz /camera/image_raw --window 30` reported a stable short-run rate around 15 Hz.

## What Failed

- WSL with `ROS_DOMAIN_ID=20` could not discover `/camera/image_raw` by multicast discovery.
- Deleting `.wslconfig` changed the WSL private IP; Windows portproxy for SSH `2222` had to be updated from `172.30.122.43:22` to `172.30.127.238:22`.
- Windows can reach WSL private SSH at `172.30.127.238:22`, but RK still cannot reach `172.30.127.238` after adding an RK route via `192.168.2.100`.

## Network Facts

- RK ROS-facing address: `192.168.2.120/24` on `eth0`.
- WSL Linux address during final retry: `172.30.127.238/20` on `eth0`.
- Windows/SSH-facing address for WSL: `192.168.2.100:2222`.
- The `192.168.2.100` address is the Windows host/port-forward side, not the WSL Linux interface.

## Conclusion

M08 passes with directed Fast DDS discovery. The working configuration is:

- RK runs `/opt/ros/humble/bin/fastdds discovery -i 0 -l 192.168.2.120 -p 11811`.
- RK camera publisher uses `ROS_DOMAIN_ID=20` and `ROS_DISCOVERY_SERVER=192.168.2.120:11811`.
- WSL subscriber uses `ROS_DOMAIN_ID=20`, `ROS_DISCOVERY_SERVER=192.168.2.120:11811`, and `ROS_SUPER_CLIENT=True`.

Default multicast discovery remains unavailable in the current WSL2 NAT setup. RK-to-WSL-private routing also remains unavailable, even after enabling Windows interface forwarding, `IPEnableRouter=1`, and `RemoteAccess`. Those limits do not block the current RK-publisher-to-WSL-subscriber image workflow.

## Evidence

- RK logs: `logs/discovery_20260710.log`, `logs/camera_20260710.log`.
- Topic list included `/camera/image_raw [sensor_msgs/msg/Image]`.
- Topic info showed one reliable publisher.
- Echo sample fields: `height=480`, `width=640`, `encoding=bgr8`, `step=1920`.
- Frequency sample: 14.99-15.22 Hz during the short `ros2 topic hz` run.
