import { OutputType } from "../../../nodes-configuration/types";

export const getFileExtension = (url: string) => {
  const extensionMatch = url.match(/\.([0-9a-z]+)(?:[\?#]|$)/i);
  return extensionMatch ? extensionMatch[1] : "";
};

export const getGeneratedFileName = (url: string, nodeName: string) => {
  const extension = getFileExtension(url);
  return `${nodeName}-output.${extension}`;
};

const extensionToTypeMap: { [key: string]: OutputType } = {
  // Image extensions
  ".png": "imageUrl",
  ".jpg": "imageUrl",
  ".gif": "imageUrl",
  ".jpeg": "imageUrl",
  ".webp": "imageUrl",
  // Video extensions
  ".mp4": "videoUrl",
  ".mov": "videoUrl",
  ".mjpg": "videoStream", // Add MJPEG support
  ".mjpeg": "videoStream", // Add MJPEG support
  // Audio extensions
  ".mp3": "audioUrl",
  ".wav": "audioUrl",
  // 3D extensions
  ".obj": "3dUrl",
  ".glb": "3dUrl",
  // Other extensions
  ".pdf": "fileUrl",
  ".txt": "fileUrl",
};

export function getOutputExtension(output: string): OutputType {
  if (!output) return "markdown";
  if (typeof output !== "string") return "markdown";

  // Check for MJPEG stream URLs specifically
  if (output.includes('/camera/') && output.includes('.mjpg')) {
    return "videoStream";
  }

  // Check for data URI base64 images
  if (output.startsWith('data:image/')) {
    return "imageBase64";
  }

  let extension = Object.keys(extensionToTypeMap).find((ext) =>
    output.endsWith(ext) || output.includes(ext + '?'), // Handle query parameters
  );

  if (!extension) {
    extension = "." + getFileTypeFromUrl(output);
  }

  return extension ? extensionToTypeMap[extension] : "markdown";
}

export function getFileTypeFromUrl(url: string) {
  const lastDotIndex = url.lastIndexOf(".");
  const urlWithoutParams = url.includes("?")
    ? url.substring(0, url.indexOf("?"))
    : url;
  const fileType = urlWithoutParams.substring(lastDotIndex + 1);
  return fileType;
}
