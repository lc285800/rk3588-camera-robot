// Copyright 2026 lc285800
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <fcntl.h>
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/select.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp/qos.hpp"
#include "sensor_msgs/msg/image.hpp"

namespace
{

struct Buffer
{
  void * start = nullptr;
  size_t length = 0;
};

int xioctl(int fd, unsigned long request, void * arg)
{
  int result = 0;
  do {
    result = ioctl(fd, request, arg);
  } while (result == -1 && errno == EINTR);
  return result;
}

uint8_t clamp_to_byte(int value)
{
  return static_cast<uint8_t>(std::clamp(value, 0, 255));
}

void yuyv_to_bgr(const uint8_t * yuyv, std::vector<uint8_t> & bgr)
{
  for (size_t src = 0, dst = 0; src + 3 < bgr.size() / 3 * 2; src += 4, dst += 6) {
    const int y0 = static_cast<int>(yuyv[src + 0]);
    const int u = static_cast<int>(yuyv[src + 1]) - 128;
    const int y1 = static_cast<int>(yuyv[src + 2]);
    const int v = static_cast<int>(yuyv[src + 3]) - 128;

    const int c0 = 298 * (y0 - 16);
    const int c1 = 298 * (y1 - 16);
    const int d = 516 * u;
    const int e = 409 * v;
    const int f = -100 * u - 208 * v;

    bgr[dst + 0] = clamp_to_byte((c0 + d + 128) >> 8);
    bgr[dst + 1] = clamp_to_byte((c0 + f + 128) >> 8);
    bgr[dst + 2] = clamp_to_byte((c0 + e + 128) >> 8);
    bgr[dst + 3] = clamp_to_byte((c1 + d + 128) >> 8);
    bgr[dst + 4] = clamp_to_byte((c1 + f + 128) >> 8);
    bgr[dst + 5] = clamp_to_byte((c1 + e + 128) >> 8);
  }
}

}  // namespace

class V4L2CameraPublisher : public rclcpp::Node
{
public:
  V4L2CameraPublisher()
  : Node("v4l2_camera_publisher")
  {
    device_ = declare_parameter<std::string>("video_device", "/dev/video1");
    frame_id_ = declare_parameter<std::string>("frame_id", "camera_link");
    topic_ = declare_parameter<std::string>("topic", "/camera/image_raw");
    reliability_ = declare_parameter<std::string>("reliability", "best_effort");
    width_ = declare_parameter<int>("image_width", 640);
    height_ = declare_parameter<int>("image_height", 480);
    frame_rate_ = declare_parameter<double>("frame_rate", 15.0);
    stats_interval_sec_ = declare_parameter<double>("stats_interval_sec", 5.0);

    open_device();
    configure_device();
    start_streaming();

    publisher_ = create_publisher<sensor_msgs::msg::Image>(topic_, make_qos());
    last_stats_time_ = now();
    timer_ = create_wall_timer(
      std::chrono::duration<double>(1.0 / frame_rate_),
      std::bind(&V4L2CameraPublisher::publish_frame, this));
    if (stats_interval_sec_ > 0.0) {
      stats_timer_ = create_wall_timer(
        std::chrono::duration<double>(stats_interval_sec_),
        std::bind(&V4L2CameraPublisher::log_stats, this));
    }

    RCLCPP_INFO(
      get_logger(), "Camera %s: %dx%d YUYV camera %.2f FPS, publishing %.2f FPS -> %s (%s)",
      device_.c_str(), width_, height_, camera_rate_, frame_rate_, topic_.c_str(),
      reliability_.c_str());
  }

  ~V4L2CameraPublisher() override
  {
    stop_streaming();
    for (const auto & buffer : buffers_) {
      if (buffer.start != nullptr && buffer.start != MAP_FAILED) {
        munmap(buffer.start, buffer.length);
      }
    }
    if (fd_ >= 0) {
      close(fd_);
    }
  }

private:
  void open_device()
  {
    fd_ = open(device_.c_str(), O_RDWR | O_NONBLOCK);
    if (fd_ < 0) {
      throw std::runtime_error("Unable to open " + device_ + ": " + strerror(errno));
    }
  }

  rclcpp::QoS make_qos() const
  {
    auto qos = rclcpp::QoS(rclcpp::KeepLast(5)).durability_volatile();
    if (reliability_ == "reliable") {
      return qos.reliable();
    }
    return qos.best_effort();
  }

  void configure_device()
  {
    v4l2_format format {};
    format.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    format.fmt.pix.width = static_cast<uint32_t>(width_);
    format.fmt.pix.height = static_cast<uint32_t>(height_);
    format.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
    format.fmt.pix.field = V4L2_FIELD_NONE;
    if (xioctl(fd_, VIDIOC_S_FMT, &format) < 0) {
      throw std::runtime_error("VIDIOC_S_FMT failed: " + std::string(strerror(errno)));
    }
    width_ = static_cast<int>(format.fmt.pix.width);
    height_ = static_cast<int>(format.fmt.pix.height);

    v4l2_streamparm stream {};
    stream.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    stream.parm.capture.timeperframe.numerator = 1;
    stream.parm.capture.timeperframe.denominator = static_cast<uint32_t>(frame_rate_);
    if (xioctl(fd_, VIDIOC_S_PARM, &stream) == 0 &&
      stream.parm.capture.timeperframe.numerator > 0)
    {
      camera_rate_ = static_cast<double>(stream.parm.capture.timeperframe.denominator) /
        static_cast<double>(stream.parm.capture.timeperframe.numerator);
    }

    v4l2_requestbuffers request {};
    request.count = 4;
    request.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    request.memory = V4L2_MEMORY_MMAP;
    if (xioctl(fd_, VIDIOC_REQBUFS, &request) < 0 || request.count < 2) {
      throw std::runtime_error("VIDIOC_REQBUFS failed");
    }

    buffers_.resize(request.count);
    for (uint32_t i = 0; i < request.count; ++i) {
      v4l2_buffer buffer {};
      buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
      buffer.memory = V4L2_MEMORY_MMAP;
      buffer.index = i;
      if (xioctl(fd_, VIDIOC_QUERYBUF, &buffer) < 0) {
        throw std::runtime_error("VIDIOC_QUERYBUF failed");
      }
      buffers_[i].length = buffer.length;
      buffers_[i].start = mmap(
        nullptr, buffer.length, PROT_READ | PROT_WRITE, MAP_SHARED, fd_, buffer.m.offset);
      if (buffers_[i].start == MAP_FAILED) {
        throw std::runtime_error("mmap failed");
      }
    }
  }

  void start_streaming()
  {
    for (uint32_t i = 0; i < buffers_.size(); ++i) {
      v4l2_buffer buffer {};
      buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
      buffer.memory = V4L2_MEMORY_MMAP;
      buffer.index = i;
      if (xioctl(fd_, VIDIOC_QBUF, &buffer) < 0) {
        throw std::runtime_error("VIDIOC_QBUF failed");
      }
    }
    v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (xioctl(fd_, VIDIOC_STREAMON, &type) < 0) {
      throw std::runtime_error("VIDIOC_STREAMON failed");
    }
    streaming_ = true;
  }

  void stop_streaming()
  {
    if (!streaming_ || fd_ < 0) {
      return;
    }
    v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    xioctl(fd_, VIDIOC_STREAMOFF, &type);
    streaming_ = false;
  }

  bool dequeue_frame(v4l2_buffer & buffer)
  {
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(fd_, &fds);
    timeval timeout {};
    timeout.tv_sec = 0;
    timeout.tv_usec = 100000;
    const int ready = select(fd_ + 1, &fds, nullptr, nullptr, &timeout);
    if (ready <= 0) {
      return false;
    }

    buffer = {};
    buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buffer.memory = V4L2_MEMORY_MMAP;
    if (xioctl(fd_, VIDIOC_DQBUF, &buffer) < 0) {
      if (errno == EAGAIN) {
        return false;
      }
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 2000, "VIDIOC_DQBUF failed: %s", strerror(errno));
      return false;
    }
    return true;
  }

  void publish_frame()
  {
    v4l2_buffer buffer {};
    if (!dequeue_frame(buffer)) {
      missed_frames_ += 1;
      return;
    }

    sensor_msgs::msg::Image message;
    message.header.stamp = now();
    message.header.frame_id = frame_id_;
    message.height = static_cast<uint32_t>(height_);
    message.width = static_cast<uint32_t>(width_);
    message.encoding = "bgr8";
    message.is_bigendian = false;
    message.step = message.width * 3;
    message.data.resize(static_cast<size_t>(height_) * static_cast<size_t>(message.step));

    const auto * yuyv = static_cast<const uint8_t *>(buffers_[buffer.index].start);
    yuyv_to_bgr(yuyv, message.data);
    publisher_->publish(std::move(message));
    published_frames_ += 1;

    if (xioctl(fd_, VIDIOC_QBUF, &buffer) < 0) {
      RCLCPP_ERROR_THROTTLE(
        get_logger(), *get_clock(), 2000, "VIDIOC_QBUF failed: %s", strerror(errno));
    }
  }

  void log_stats()
  {
    const auto current_time = now();
    const double elapsed = (current_time - last_stats_time_).seconds();
    if (elapsed <= 0.0) {
      return;
    }
    const uint64_t frames = published_frames_ - last_stats_frames_;
    RCLCPP_INFO(
      get_logger(), "Published %lu frames in %.2fs (%.2f FPS), total=%lu, missed=%lu",
      frames, elapsed, static_cast<double>(frames) / elapsed, published_frames_,
      missed_frames_);
    last_stats_frames_ = published_frames_;
    last_stats_time_ = current_time;
  }

  std::string device_;
  std::string frame_id_;
  std::string topic_;
  std::string reliability_;
  int width_ = 640;
  int height_ = 480;
  double frame_rate_ = 15.0;
  double camera_rate_ = 15.0;
  double stats_interval_sec_ = 5.0;
  int fd_ = -1;
  bool streaming_ = false;
  std::vector<Buffer> buffers_;
  uint64_t published_frames_ = 0;
  uint64_t last_stats_frames_ = 0;
  uint64_t missed_frames_ = 0;
  rclcpp::Time last_stats_time_;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::TimerBase::SharedPtr stats_timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try {
    rclcpp::spin(std::make_shared<V4L2CameraPublisher>());
  } catch (const std::exception & error) {
    RCLCPP_FATAL(rclcpp::get_logger("v4l2_camera_publisher"), "%s", error.what());
    rclcpp::shutdown();
    return 1;
  }
  rclcpp::shutdown();
  return 0;
}
