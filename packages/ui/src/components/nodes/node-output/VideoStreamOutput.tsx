import React, { memo } from "react";
import styled from "styled-components";

interface VideoStreamOutputProps {
  streamUrl: string;
  name: string;
  lastRun?: string;
}

const VideoStreamOutput: React.FC<VideoStreamOutputProps> = ({
  streamUrl,
  name,
  lastRun,
}) => {
  return (
    <StreamContainer>
      <StreamImage
        src={streamUrl}
        alt={`${name} - Live Camera Stream`}
        onError={(e) => {
          console.error("Stream error:", e);
          // Optionally show error message or fallback
        }}
      />
      <StreamLabel>Live Stream - {name}</StreamLabel>
    </StreamContainer>
  );
};

const StreamContainer = styled.div`
  position: relative;
  margin-top: 10px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #000;
`;

const StreamImage = styled.img`
  display: block;
  width: 100%;
  height: auto;
  border-radius: 8px;
`;

const StreamLabel = styled.div`
  position: absolute;
  bottom: 8px;
  left: 8px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
`;

function arePropsEqual(
  prevProps: VideoStreamOutputProps,
  nextProps: VideoStreamOutputProps,
) {
  return (
    prevProps.streamUrl === nextProps.streamUrl &&
    prevProps.lastRun === nextProps.lastRun
  );
}

export default memo(VideoStreamOutput, arePropsEqual);