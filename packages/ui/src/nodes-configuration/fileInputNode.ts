import { NodeConfig } from "./types";

const fileInputNodeConfig: NodeConfig = {
  nodeName: "File Input",
  processorType: "file-input",
  icon: "AiOutlineFile",
  fields: [
    {
      type: "fileUpload",
      name: "file_url",
      required: true,
      placeholder: "Upload a file",
      description: "Select a file to upload and use in the workflow"
    },
    {
      type: "input",
      name: "file_name",
      required: false,
      placeholder: "File name (optional)",
      description: "Optional custom name for the file"
    }
  ],
  outputType: "fileUrl",
  defaultHideOutput: true,
  section: "input",
  helpMessage: "fileInputHelp",
};

export default fileInputNodeConfig;