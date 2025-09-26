import { NodeConfig } from "./types";

const cameraInputNodeConfig: NodeConfig = {
  nodeName: "Camera Input (Streaming)",
  processorType: "camera-input",
  icon: "AiOutlineCamera",
  fields: [
    {
      type: "input",
      name: "camera_index",
      required: false,
      placeholder: "0",
      description: "Camera index (0 for default camera)"
    },
    {
      type: "input",
      name: "resolution_width",
      required: false,
      placeholder: "640",
      description: "Camera resolution width"
    },
    {
      type: "input",
      name: "resolution_height",
      required: false,
      placeholder: "480",
      description: "Camera resolution height"
    },
    {
      type: "input",
      name: "target_fps",
      required: false,
      placeholder: "15",
      description: "Target frames per second"
    },
    {
      type: "select",
      name: "stream_mode",
      required: false,
      placeholder: "1",
      description: "Stream mode",
      options: [
        { value: "0", label: "Single Shot" },
        { value: "1", label: "Streaming" }
      ]
    },
    {
      type: "select",
      name: "output_type",
      required: false,
      placeholder: "videoStream",
      description: "Output type",
      options: [
        { value: "videoStream", label: "Video Stream (MJPEG)" },
        { value: "imageBase64", label: "Base64 Image" }
      ]
    },
    {
      type: "input",
      name: "jpeg_quality",
      required: false,
      placeholder: "85",
      description: "JPEG quality (1-100)"
    },
    {
      type: "input",
      name: "read_attempts",
      required: false,
      placeholder: "5",
      description: "Frame read attempts"
    },
    {
      type: "input",
      name: "warmup_ms",
      required: false,
      placeholder: "150",
      description: "Camera warmup time (ms)"
    },
    {
      type: "input",
      name: "init_timeout_ms",
      required: false,
      placeholder: "1500",
      description: "Initialization timeout (ms)"
    }
  ],
  // Dynamic output type based on configuration
  outputType: "videoStream", // Default to video stream
  defaultHideOutput: false,
  section: "input",
  helpMessage: "cameraInputHelp",
};

export default cameraInputNodeConfig;