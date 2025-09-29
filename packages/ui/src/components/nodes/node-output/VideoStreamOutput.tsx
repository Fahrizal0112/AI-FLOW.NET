import React, { memo, useState, useEffect, useRef, useContext } from "react";
import styled from "styled-components";
import { FaStop } from "react-icons/fa";
import { SocketContext } from "../../../providers/SocketProvider";

interface VideoStreamOutputProps {
  streamUrl: string;
  name: string;
  lastRun?: string;
  nodeId?: string;
}

const VideoStreamOutput: React.FC<VideoStreamOutputProps> = ({
  streamUrl,
  name,
  lastRun,
  nodeId,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [isStopping, setIsStopping] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout>();
  const { emitEvent } = useContext(SocketContext);

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    setRetryCount(0);
    setIsStopping(false);
    
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
    if (retryCount < 5 && !isStopping) {
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

  const handleStopStream = () => {
    if (!nodeId) {
      console.warn("No nodeId provided, cannot stop stream");
      return;
    }

    setIsStopping(true);
    
    const event = {
      name: "cancel_node" as const,
      data: {
        jsonFile: "",
        nodeName: nodeId, // This will use either the React Flow ID or data.name
      },
    };

    const success = emitEvent(event);
    if (success) {
      console.log(`Stop request sent for node: ${nodeId}`);
      // Clear retry timeout if stopping
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    } else {
      console.error("Failed to send stop request");
      setIsStopping(false);
    }
  };

  // Add debugging at the beginning of component
  useEffect(() => {
    console.log("VideoStreamOutput props:", { streamUrl, name, lastRun, nodeId });
    console.log("Should show stop button:", !!nodeId);
    console.log("NodeId type:", typeof nodeId, "Value:", nodeId);
  }, [streamUrl, name, lastRun, nodeId]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  // Add debugging at the beginning of component
  useEffect(() => {
    console.log("VideoStreamOutput props:", { streamUrl, name, lastRun, nodeId });
    console.log("Should show stop button:", !!nodeId);
  }, [streamUrl, name, lastRun, nodeId]);

  return (
    <StreamContainer>
      {nodeId && (
        <StopButton
          onClick={handleStopStream}
          disabled={isStopping}
          title="Stop camera stream"
        >
          <FaStop />
        </StopButton>
      )}
      
      {/* Add the missing StreamImage element */}
      <StreamImage
        ref={imgRef}
        src={streamUrl}
        alt={`Live stream from ${name}`}
        onLoad={handleLoad}
        onError={handleError}
        style={{
          opacity: isLoading || hasError || isStopping ? 0.3 : 1,
          display: 'block'
        }}
      />

      {/* Loading overlay */}
      {isLoading && (
        <LoadingOverlay>
          <LoadingText>
            {retryCount === 0 ? "Loading stream..." : `Reconnecting ${retryCount}/5...`}
          </LoadingText>
        </LoadingOverlay>
      )}

      {/* Error overlay */}
      {hasError && retryCount >= 5 && (
        <ErrorOverlay>
          <ErrorText>
            Stream disconnected
            <br />
            <small>Check camera connection</small>
          </ErrorText>
        </ErrorOverlay>
      )}

      {/* Stopped overlay */}
      {isStopping && (
        <StoppedOverlay>
          <StoppedText>
            Stopping stream...
            <br />
            <small>Please wait</small>
          </StoppedText>
        </StoppedOverlay>
      )}
      
      <StreamLabel>
        Live Stream - {name}
        {isLoading && retryCount === 0 && " (Loading...)"}
        {isLoading && retryCount > 0 && ` (Reconnecting ${retryCount}/5...)`}
        {hasError && retryCount >= 5 && " (Disconnected)"}
        {isStopping && " (Stopping...)"}
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

const StopButton = styled.button`
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background-color: #ff4444;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 3;
  
  &:hover:not(:disabled) {
    background-color: #cc0000;
    transform: scale(1.1);
  }
  
  &:disabled {
    background-color: #666;
    cursor: not-allowed;
    opacity: 0.6;
  }
  
  svg {
    font-size: 12px;
  }
`;

const StoppedOverlay = styled.div`
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

const StoppedText = styled.div`
  color: #ffa500;
  font-size: 14px;
  text-align: center;
  
  small {
    font-size: 12px;
    color: #ccc;
  }
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