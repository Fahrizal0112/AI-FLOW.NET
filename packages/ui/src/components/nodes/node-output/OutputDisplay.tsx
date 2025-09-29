import MarkdownOutput from "./MarkdownOutput";
import { NodeData } from "../types/node";
import { useTranslation } from "react-i18next";
import { FiFile } from "react-icons/fi";
import ImageUrlOutput from "./ImageUrlOutput";
import ImageBase64Output from "./ImageBase64Output";
import VideoUrlOutput from "./VideoUrlOutput";
import VideoStreamOutput from "./VideoStreamOutput";
import AudioUrlOutput from "./AudioUrlOutput";
import { getOutputExtension } from "./outputUtils";
import PdfUrlOutput from "./PdfUrlOutput";
import { OutputType } from "../../../nodes-configuration/types";
import { useState } from "react";
import ThreeDimensionalUrlOutput from "./ThreeDimensionalUrlOutput";

interface OutputDisplayProps {
  data: NodeData;
  getOutputComponentOverride?: (
    data: NodeData,
    outputType: OutputType,
  ) => JSX.Element | null;
}

export default function OutputDisplay({
  data,
  getOutputComponentOverride,
}: OutputDisplayProps) {
  const { t } = useTranslation("flow");

  // Add more detailed debugging
  console.log("OutputDisplay data:", data);
  console.log("OutputDisplay data.id:", data.id);
  console.log("OutputDisplay data keys:", Object.keys(data));

  const [indexDisplayed, setIndexDisplayed] = useState(0);
  
  const nbOutput =
    data.outputData != null && typeof data.outputData !== "string"
      ? data.outputData.length
      : 1;

  const getOutputComponent = () => {
    if (getOutputComponentOverride) {
      const override = getOutputComponentOverride(data, getOutputType());
      if (override) {
        return override;
      }
    }

    if (!data.outputData) {
      console.log("No outputData available");
      return <></>;
    }

    let output = data.outputData;

    if (typeof output !== "string") {
      output = output[indexDisplayed];
    }

    const outputType = getOutputType();
    console.log("Final outputType:", outputType);
    console.log("Final output:", output);

    switch (outputType) {
      case "imageUrl":
        return <ImageUrlOutput url={output} name={data.name} />;
      case "imageBase64":
        console.log("Rendering ImageBase64Output");
        return (
          <ImageBase64Output
            data={output}
            name={data.name}
            lastRun={data.lastRun}
          />
        );
      case "videoUrl":
        return <VideoUrlOutput url={output} name={data.name} />;
      case "videoStream":
        console.log("Rendering VideoStreamOutput with nodeId:", data.id || data.name);
        return <VideoStreamOutput 
          streamUrl={output} 
          name={data.name} 
          lastRun={data.lastRun} 
          nodeId={data.id || data.name} 
        />;
      case "imageBase64":
        return (
          <ImageBase64Output
            data={output}
            name={data.name}
            lastRun={data.lastRun}
          />
        );
      case "audioUrl":
        return <AudioUrlOutput url={output} name={data.name} />;
      case "3dUrl":
        return <ThreeDimensionalUrlOutput url={output} name={data.name} />;
      case "pdfUrl":
        return <PdfUrlOutput url={output} name={data.name} />;
      case "fileUrl":
        return (
          <a href={output} target="_blank" rel="noreferrer">
            <div className="flex flex-row items-center justify-center space-x-2 py-2 hover:text-sky-400">
              <FiFile className="text-4xl" />
              <p>{t("FileUploaded")}</p>
            </div>
          </a>
        );
      default:
        return (
          <MarkdownOutput
            data={output}
            name={data.name}
            appearance={data.appearance}
          />
        );
    }
  };

  function getOutputType(): OutputType {
    console.log("getOutputType - data.config?.outputType:", data.config?.outputType);
    console.log("getOutputType - data.output_type:", data.output_type);
    console.log("getOutputType - data.outputData:", data.outputData);
    
    if (data.config?.outputType) {
      console.log("Using config outputType:", data.config.outputType);
      return data.config.outputType;
    }

    if (!data.outputData) {
      console.log("No outputData, returning markdown");
      return "markdown";
    }

    let outputData = data.outputData;
    let output = "";

    if (typeof outputData !== "string") {
      output = outputData[indexDisplayed];
    } else {
      output = outputData;
    }

    const outputType = getOutputExtension(output);
    console.log("Detected outputType from extension:", outputType);

    return outputType;
  }

  return (
    <div className="flex h-full w-full flex-col">
      {nbOutput > 1 && typeof data.outputData !== "string" && (
        <div className="mt-2 flex flex-row items-center justify-center gap-1 overflow-x-auto p-1">
          {data?.outputData?.map((output, index) => (
            <button
              key={index}
              className={`rounded-full ${index === indexDisplayed ? "bg-orange-400" : "bg-gray-500 hover:bg-orange-200"} whitespace-nowrap p-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400`}
              onClick={() => setIndexDisplayed(index)}
              aria-label={`View output ${index + 1}`}
              title={`Output ${index + 1}`}
            />
          ))}
        </div>
      )}
      {getOutputComponent()}
    </div>
  );
}
