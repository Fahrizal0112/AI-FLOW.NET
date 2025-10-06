import dallENodeConfig from "./dallENode";
import inputTextNodeConfig from "./inputTextNode";
import { llmPromptNodeConfig } from "./llmPrompt";
import stableDiffusionStabilityAiNodeConfig from "./stableDiffusionStabilityAiNode";
import { urlNodeConfig } from "./urlNode";
import { youtubeTranscriptNodeConfig } from "./youtubeTranscriptNode";
import { mergerPromptNode } from "./mergerPromptNode";
import { gptVisionNodeConfig } from "./gptVisionNode";
import fileInputNodeConfig from "./fileInputNode";
import cameraInputNodeConfig from "./cameraInputNode";
import { FieldType, NodeConfig } from "./types";
import { getNodeExtensions } from "../api/nodes";
import withCache from "../api/cache/withCache";

export const nodeConfigs: { [key: string]: NodeConfig | undefined } = {
  "input-text": inputTextNodeConfig,
  url_input: urlNodeConfig,
  "llm-prompt": llmPromptNodeConfig,
  "gpt-vision": gptVisionNodeConfig,
  youtube_transcript_input: youtubeTranscriptNodeConfig,
  "dalle-prompt": dallENodeConfig,
  "stable-diffusion-stabilityai-prompt": stableDiffusionStabilityAiNodeConfig,
  "merger-prompt": mergerPromptNode,
  "file-input": fileInputNodeConfig,
  "camera-input": cameraInputNodeConfig,
};

const fieldTypeWithoutHandle: FieldType[] = [
  "select",
  "option",
  "boolean",
  "slider",
];

export const getConfigViaType = (type: string): NodeConfig | undefined => {
  return structuredClone(nodeConfigs[type]);
};

export const fieldHasHandle = (fieldType: FieldType): boolean => {
  return !fieldTypeWithoutHandle.includes(fieldType);
};

export const loadExtensions = async () => {
  console.log("🔄 Loading extensions...");
  try {
    const extensions = await withCache(getNodeExtensions);
    console.log("📦 Extensions received:", extensions);
    console.log("📦 Number of extensions:", extensions.length);
    
    extensions.forEach((extension: NodeConfig) => {
      const key = extension.processorType;
      console.log(`🔍 Processing extension: ${extension.nodeName} (${key})`);
      
      if (!key) {
        console.warn("⚠️ Extension missing processorType:", extension);
        return;
      }
      
      if (key in nodeConfigs) {
        console.log(`⚠️ Extension already exists: ${key}`);
        return;
      }

      nodeConfigs[key] = extension;
      console.log(`✅ Added extension: ${extension.nodeName} (${key})`);
    });
    
    console.log("📋 Final nodeConfigs keys:", Object.keys(nodeConfigs));
    console.log("🎯 YOLO extension in nodeConfigs:", nodeConfigs["yolo-detection-processor"]);
  } catch (error) {
    console.error("❌ Error loading extensions:", error);
  }
};
