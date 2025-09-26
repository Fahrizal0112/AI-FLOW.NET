import React, { memo, useState, useEffect, useRef } from "react";
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
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const imgRef = useRef<HTMLImageElement>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    setRetryCount(0);
    
    // Clear any existing retry timeout
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }
  }, [streamUrl]);

  const handleLoad = () => {
    console.log("Stream loaded successfully:", streamUrl);
    setIsLoading(false);
    setHasError(false);
    setRetryCount(0);
  };

  const handleError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    console.error("Stream error:", e);
    console.error("Failed URL:", streamUrl);
    setIsLoading(false);
    setHasError(true);
    
    // Auto retry up to 5 times for streaming
    if (retryCount < 5) {
      console.log(`Retrying stream ${retryCount + 1}/5...`);
      retryTimeoutRef.current = setTimeout(() => {
        setRetryCount(prev => prev + 1);
        setIsLoading(true);
        setHasError(false);
        
        // Force reload by adding timestamp to prevent caching
        if (imgRef.current) {
          const url = new URL(streamUrl);
          url.searchParams.set('t', Date.now().toString());
          imgRef.current.src = url.toString();
        }
      }, 1000 * Math.min(retryCount + 1, 3)); // Max 3 second delay
    }
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  // Add debugging
  useEffect(() => {
    console.log("VideoStreamOutput props:", { streamUrl, name, lastRun });
  }, [streamUrl, name, lastRun]);

  return (
    <StreamContainer>
      {isLoading && (
        <LoadingOverlay>
          <LoadingText>
            {retryCount > 0 ? `Reconnecting... (${retryCount}/5)` : "Loading camera stream..."}
          </LoadingText>
        </LoadingOverlay>
      )}
      
      {hasError && retryCount >= 5 && (
        <ErrorOverlay>
          <ErrorText>
            Camera stream unavailable
            <br />
            <small>Check camera connection and permissions</small>
            <br />
            <small>URL: {streamUrl}</small>
          </ErrorText>
        </ErrorOverlay>
      )}
      
      <StreamImage
        ref={imgRef}
        src={streamUrl}
        alt={`${name} - Live Camera Stream`}
        onLoad={handleLoad}
        onError={handleError}
        crossOrigin="anonymous"
        style={{ 
          display: hasError && retryCount >= 5 ? 'none' : 'block',
          opacity: isLoading ? 0.3 : 1
        }}
      />
      
      <StreamLabel>
        Live Stream - {name}
        {isLoading && retryCount === 0 && " (Loading...)"}
        {isLoading && retryCount > 0 && ` (Reconnecting ${retryCount}/5...)`}
        {hasError && retryCount >= 5 && " (Disconnected)"}
      </StreamLabel>
    </StreamContainer>
  );
};

const StreamContainer = styled.div`
  position: relative;
  margin-top: 10px;
  border-radius: 8px;
  overflow: hidden;
  background-color: #000;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const StreamImage = styled.img`
  display: block;
  width: 100%;
  height: auto;
  border-radius: 8px;
  transition: opacity 0.3s ease;
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.8);
  z-index: 1;
`;

const ErrorOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(40, 40, 40, 0.9);
  z-index: 1;
`;

const LoadingText = styled.div`
  color: white;
  font-size: 14px;
  text-align: center;
`;

const ErrorText = styled.div`
  color: #ff6b6b;
  font-size: 14px;
  text-align: center;
  
  small {
    font-size: 12px;
    color: #ccc;
  }
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
  z-index: 2;
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