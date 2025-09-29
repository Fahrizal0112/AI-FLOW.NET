import { NodeConfig } from "./types";

const cameraInputNodeConfig: NodeConfig = {
  nodeName: "Camera Input (Streaming)",
  processorType: "camera-input",
  icon: "AiOutlineCamera",
  fields: [
    {
      type: "input",
      name: "camera_index",
      label: "📹 Camera Index",
      required: false,
      placeholder: "0",
      description: "📹 Camera Device Index - Camera device index (0 for default camera)"
    },
    {
      type: "input",
      name: "resolution_width",
      label: "📐 Width",
      required: false,
      placeholder: "640",
      description: "📐 Resolution Width - Camera resolution width"
    },
    {
      type: "input",
      name: "resolution_height",
      label: "📐 Height",
      required: false,
      placeholder: "480",
      description: "📐 Resolution Height - Camera resolution height"
    },
    {
      type: "input",
      name: "target_fps",
      label: "🎯 FPS",
      required: false,
      placeholder: "15",
      description: "🎯 Target Frame Rate (FPS) - Target frames per second"
    },
    {
      type: "select",
      name: "stream_mode",
      label: "📺 Stream Mode",
      required: false,
      placeholder: "1",
      description: "📺 Camera Stream Mode - Camera capture mode",
      options: [
        { value: "0", label: "📸 Single Shot" },
        { value: "1", label: "🎥 Continuous Streaming" }
      ]
    },
    {
      type: "select",
      name: "output_type",
      label: "📤 Output Type",
      required: false,
      placeholder: "videoStream",
      description: "📤 Output Format Type - Choose between live video stream or base64 image output",
      options: [
        { value: "videoStream", label: "🎥 Live Video Stream (MJPEG)" },
        { value: "imageBase64", label: "🖼️ Static Base64 Image" }
      ]
    },
    {
      type: "input",
      name: "jpeg_quality",
      label: "🖼️ JPEG Quality",
      required: false,
      placeholder: "85",
      description: "🖼️ JPEG Quality - JPEG compression quality (1-100)"
    },
    {
      type: "input",
      name: "read_attempts",
      label: "🔄 Read Attempts",
      required: false,
      placeholder: "5",
      description: "🔄 Frame Read Attempts - Number of frame read attempts"
    },
    {
      type: "input",
      name: "warmup_ms",
      label: "⏱️ Warmup Time",
      required: false,
      placeholder: "150",
      description: "⏱️ Camera Warmup Time (ms) - Camera warmup time in milliseconds"
    },
    {
      type: "input",
      name: "init_timeout_ms",
      label: "⏰ Init Timeout",
      required: false,
      placeholder: "1500",
      description: "⏰ Initialization Timeout (ms) - Max wait time for first frame in streaming mode"
    }
  ],
  // Dynamic output type based on configuration
  outputType: "videoStream", // Default to video stream
  defaultHideOutput: false,
  section: "input",
  helpMessage: "cameraInputHelp",
  showHandlesNames: true, // Ini yang penting untuk menampilkan label!
};

export default cameraInputNodeConfig;