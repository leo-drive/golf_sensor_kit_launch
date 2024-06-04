# # Copyright 2020 Tier IV, Inc. All rights reserved.
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.

import launch
from launch.actions import DeclareLaunchArgument
from launch.actions import SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.substitutions.launch_configuration import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare
from launch.actions import OpaqueFunction
from launch.substitutions import PathJoinSubstitution
from launch.substitutions import EnvironmentVariable
import yaml


def launch_setup(context, *args, **kwargs):
    output_topic = LaunchConfiguration("output_topic").perform(context)

    image_name = LaunchConfiguration("input_image").perform(context)
    camera_name = LaunchConfiguration("camera_name").perform(context)
    camera_namespace = "/sensing/camera/" + image_name

    # tensorrt params
    gpu_id = int(LaunchConfiguration("gpu_id").perform(context))
    calib_image_directory = FindPackageShare("tensorrt_yolox").perform(context) + "/calib_image/"
    tensorrt_config_path = FindPackageShare('tensorrt_yolox').perform(context) + "/config/yolox_s_plus_opt.param.yaml"
    precision = LaunchConfiguration("precision").perform(context)
    data_path = PathJoinSubstitution([EnvironmentVariable('HOME'), 'autoware_data'])
    model_path = PathJoinSubstitution([data_path, 'tensorrt_yolox/'])

    with open(tensorrt_config_path, "r") as f:
        tensorrt_yaml_param = yaml.safe_load(f)["/**"]["ros__parameters"]

    camera_param_path = FindPackageShare("individual_params").perform(
        context) + "/config/default/golf_sensor_kit/camera_params/" + image_name + ".param.yaml"
    with open(camera_param_path, "r") as f:
        camera_yaml_param = yaml.safe_load(f)["/**"]["ros__parameters"]

    container = ComposableNodeContainer(
        name=camera_name + "_camera_container",
        namespace="/perception/object_detection",
        package="rclcpp_components",
        executable=LaunchConfiguration("container_executable"),
        output="screen",
        composable_node_descriptions=[
            ComposableNode(
                package="arena_camera",
                plugin="arena_camera::ArenaCameraNode",
                name=camera_name + "_camera_node",
                parameters=[{"camera_name": camera_yaml_param['camera_name'],
                             "frame_id": camera_yaml_param['frame_id'],
                             "pixel_format": camera_yaml_param['pixel_format'],
                             "serial_no": camera_yaml_param['serial_no'],
                             "camera_info_url": camera_yaml_param['camera_info_url'],
                             "fps": camera_yaml_param['fps'],
                             "horizontal_binning": camera_yaml_param['horizontal_binning'],
                             "vertical_binning": camera_yaml_param['vertical_binning'],
                             "use_default_device_settings": camera_yaml_param['use_default_device_settings'],
                             "enable_rectifying": camera_yaml_param['enable_rectifying'],
                             "enable_compressing": camera_yaml_param['enable_compressing'],
                             "exposure_auto": camera_yaml_param['exposure_auto'],
                             "exposure_value": camera_yaml_param['exposure_value'],
                             "exposure_auto_limit_auto": camera_yaml_param['exposure_auto_limit_auto'],
                             "exposure_auto_lower_limit": camera_yaml_param['exposure_auto_lower_limit'],
                             "exposure_auto_upper_limit": camera_yaml_param['exposure_auto_upper_limit'],
                             "exposure_damping": camera_yaml_param['exposure_damping'],
                             "balance_white_auto": camera_yaml_param['balance_white_auto'],
                             "balance_ratio_selector": camera_yaml_param['balance_ratio_selector'],
                             "gain_auto": camera_yaml_param['gain_auto'],
                             "gain_value": camera_yaml_param['gain_value'],
                             "target_brightness": camera_yaml_param['target_brightness'],
                             "lut_enable": camera_yaml_param['lut_enable'],
                             "use_ptp": camera_yaml_param['use_ptp'],
                             "balance_ratio.red": 3.0,
                             "balance_ratio.green": 2.0,
                             "balance_ratio.blue": 3.0,
                             "use_ptp": camera_yaml_param['use_ptp'],
                             "use_ptp": camera_yaml_param['use_ptp'],
                             }],
                remappings=[
                ],
                extra_arguments=[
                    {"use_intra_process_comms": True}
                ],
            ),
            ComposableNode(
                package="tensorrt_yolox",
                plugin="tensorrt_yolox::TrtYoloXNode",
                name=["tensorrt_yolox", LaunchConfiguration("camera_id")],
                namespace=["/perception/object_recognition/detection"],
                remappings=[
                  (
                    "~/in/image",
                    [
                      "/sensing/camera/camera",
                      LaunchConfiguration("camera_id"),
                      "/image_rect_color",
                    ],
                  ),
                  (
                    "~/out/objects",
                    [
                      "/perception/object_recognition/detection/rois",
                      LaunchConfiguration("camera_id"),
                    ],
                  ),
                  (
                    "~/out/image",
                    [
                      "/perception/object_recognition/detection/rois",
                      LaunchConfiguration("camera_id"),
                      "/debug/image",
                    ],
                  ),
                  (
                    "~/out/image/compressed",
                    [
                      "/perception/object_recognition/detection/rois",
                      LaunchConfiguration("camera_id"),
                      "/debug/image/compressed",
                    ],
                  ),
                  (
                    "~/out/image/compressedDepth",
                    [
                      "/perception/object_recognition/detection/rois",
                      LaunchConfiguration("camera_id"),
                      "/debug/image/compressedDepth",
                    ],
                  ),
                  (
                    "~/out/image/theora",
                    [
                      "/perception/object_recognition/detection/rois",
                      LaunchConfiguration("camera_id"),
                      "/debug/image/theora",
                    ],
                  ),
                ],
                parameters=[
                    {
                      "score_threshold": tensorrt_yaml_param['score_threshold'],
                      "nms_threshold": tensorrt_yaml_param['nms_threshold'],
                      "precision": precision,  # FP16, FP32, INT8
                      "data_path": data_path,
                      "model_path": model_path.perform(context) + LaunchConfiguration("model_name").perform(context) + ".onnx",
                      "label_path": model_path.perform(context) + "/label.txt",
                      "clip_value": tensorrt_yaml_param['clip_value'],
                      "preprocess_on_gpu": tensorrt_yaml_param['preprocess_on_gpu'],
                      "calibration_image_list_path": tensorrt_yaml_param['calibration_image_list_path'],
                      "calibration_algorithm": tensorrt_yaml_param['calibration_algorithm'],
                      "dla_core_id": tensorrt_yaml_param['dla_core_id'],
                      "quantize_first_layer": tensorrt_yaml_param['quantize_first_layer'],
                      "quantize_last_layer": tensorrt_yaml_param['quantize_last_layer'],
                      "profile_per_layer": tensorrt_yaml_param['profile_per_layer'],
                    }
                ],
                extra_arguments=[{"use_intra_process_comms": LaunchConfiguration("use_intra_process")}],
            ),

        ],

    )
    return [container]


def generate_launch_description():
    launch_arguments = []

    def add_launch_arg(name: str, default_value=None, description=None):
        # a default_value of None is equivalent to not passing that kwarg at all
        launch_arguments.append(
            DeclareLaunchArgument(name, default_value=default_value, description=description)
        )

    add_launch_arg("input_image", "", description="input camera topic")
    add_launch_arg("camera_name", "")
    add_launch_arg("label_file", "", description="tensorrt node label file")
    add_launch_arg("gpu_id", "", description="gpu setting")
    add_launch_arg("camera_id", "", description="camera_id")
    add_launch_arg("use_intra_process", "", "use intra process")
    add_launch_arg("use_multithread", "", "use multithread")
    add_launch_arg("precision", "int8")

    add_launch_arg("model_name", "yolox-sPlus-T4-960x960-pseudo-finetune", description="yolo model type")

    set_container_executable = SetLaunchConfiguration(
        "container_executable",
        "component_container",
        condition=UnlessCondition(LaunchConfiguration("use_multithread")),
    )

    set_container_mt_executable = SetLaunchConfiguration(
        "container_executable",
        "component_container_mt",
        condition=IfCondition(LaunchConfiguration("use_multithread")),
    )

    return launch.LaunchDescription(
        launch_arguments
        + [set_container_executable, set_container_mt_executable]
        + [OpaqueFunction(function=launch_setup)]
    )