cmake_minimum_required(VERSION 3.8)
project(lubanvision_camera_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

add_executable(v4l2_camera_publisher src/v4l2_camera_publisher.cpp)
target_compile_features(v4l2_camera_publisher PUBLIC cxx_std_17)
ament_target_dependencies(v4l2_camera_publisher rclcpp sensor_msgs)

add_executable(image_rate_probe src/image_rate_probe.cpp)
target_compile_features(image_rate_probe PUBLIC cxx_std_17)
ament_target_dependencies(image_rate_probe rclcpp sensor_msgs)

install(TARGETS v4l2_camera_publisher
  image_rate_probe
  DESTINATION lib/${PROJECT_NAME})

ament_package()
