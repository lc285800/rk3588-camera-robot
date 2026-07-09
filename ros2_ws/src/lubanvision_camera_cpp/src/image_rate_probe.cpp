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

#include <chrono>
#include <cstdint>
#include <string>
#include <thread>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"

class ImageRateProbe : public rclcpp::Node
{
public:
  ImageRateProbe()
  : Node("image_rate_probe_cpp")
  {
    topic_ = declare_parameter<std::string>("topic", "/camera/image_raw");
    reliability_ = declare_parameter<std::string>("reliability", "best_effort");
    duration_sec_ = declare_parameter<double>("duration_sec", 15.0);
    expected_width_ = declare_parameter<int>("expected_width", 640);
    expected_height_ = declare_parameter<int>("expected_height", 480);
    expected_encoding_ = declare_parameter<std::string>("expected_encoding", "bgr8");
    start_time_ = now();

    subscription_ = create_subscription<sensor_msgs::msg::Image>(
      topic_, make_qos(),
      std::bind(&ImageRateProbe::on_image, this, std::placeholders::_1));
    timer_ = create_wall_timer(
      std::chrono::milliseconds(200), std::bind(&ImageRateProbe::maybe_finish, this));
    RCLCPP_INFO(get_logger(), "Counting %s for %.1fs", topic_.c_str(), duration_sec_);
  }

  bool done() const
  {
    return done_;
  }

private:
  rclcpp::QoS make_qos() const
  {
    auto qos = rclcpp::QoS(rclcpp::KeepLast(5)).durability_volatile();
    if (reliability_ == "reliable") {
      return qos.reliable();
    }
    return qos.best_effort();
  }

  void on_image(const sensor_msgs::msg::Image::SharedPtr message)
  {
    const auto current_time = now();
    if (!first_frame_seen_) {
      first_time_ = current_time;
      first_frame_seen_ = true;
    }
    last_time_ = current_time;
    frames_ += 1;

    if (
      message->width != static_cast<uint32_t>(expected_width_) ||
      message->height != static_cast<uint32_t>(expected_height_) ||
      message->encoding != expected_encoding_)
    {
      bad_frames_ += 1;
    }
  }

  void maybe_finish()
  {
    if (done_) {
      return;
    }
    const auto current_time = now();
    const double elapsed = (current_time - start_time_).seconds();
    if (elapsed < duration_sec_) {
      return;
    }

    double sample_span = 0.0;
    if (first_frame_seen_) {
      sample_span = (last_time_ - first_time_).seconds();
    }
    const double fps = sample_span > 0.0 ? static_cast<double>(frames_) / sample_span : 0.0;
    RCLCPP_INFO(
      get_logger(), "Received %lu frames in %.2fs (%.2f FPS), bad_frames=%lu",
      frames_, sample_span, fps, bad_frames_);
    done_ = true;
  }

  std::string topic_;
  std::string reliability_;
  std::string expected_encoding_;
  double duration_sec_ = 15.0;
  int expected_width_ = 640;
  int expected_height_ = 480;
  bool done_ = false;
  bool first_frame_seen_ = false;
  uint64_t frames_ = 0;
  uint64_t bad_frames_ = 0;
  rclcpp::Time start_time_;
  rclcpp::Time first_time_;
  rclcpp::Time last_time_;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ImageRateProbe>();
  while (rclcpp::ok() && !node->done()) {
    rclcpp::spin_some(node);
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  rclcpp::shutdown();
  return 0;
}
