import React, { memo, useState, useEffect, useCallback } from "react";
import styled from "styled-components";

interface CameraStreamOutputProps {
  imageData: string;
  name: string;
  lastRun?: string;
}

const CameraStreamOutput: React.FC<CameraStreamOutputProps> = ({
  imageData,
  name,
  lastRun,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [currentImage, setCurrentImage] = useState<string>(imageData);

  // Auto-refresh when imageData changes
  useEffect(() => {
    if (imageData && imageData.startsWith('data:image/')) {
      setCurrentImage(imageData);
      setHasError(false);
      setIsLoading(false);
    } else if (imageData && !imageData.startsWith('data:image/')) {
      // Handle non-base64 URLs (fallback)
      setCurrentImage(imageData);
      setHasError(false);
    }
  }, [imageData]);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);
  }, []);

  const handleError = useCallback((e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    console.error('Image load error:', e);
    setIsLoading(false);
    setHasError(true);
  }, []);

  if (!currentImage) {
    return (
      <StreamContainer>
        <ErrorOverlay>
          <ErrorText>
            No camera data available
            <br />
            <small>Check camera connection and run the node</small>
          </ErrorText>
        </ErrorOverlay>
      </StreamContainer>
    );
  }

  return (
    <StreamContainer>
      {isLoading && (
        <LoadingOverlay>
          <LoadingText>Loading camera stream...</LoadingText>
        </LoadingOverlay>
      )}
      
      {hasError && (
        <ErrorOverlay>
          <ErrorText>
            Failed to load camera image
            <br />
            <small>Check camera connection</small>
          </ErrorText>
        </ErrorOverlay>
      )}
      
      <StreamImage
        src={currentImage}
        alt="Camera Stream"
        onLoad={handleLoad}
        onError={handleError}
        style={{ 
          opacity: isLoading || hasError ? 0 : 1,
          display: hasError ? 'none' : 'block'
        }}
      />
      
      <StreamLabel>
        {name} {lastRun && `(${new Date(lastRun).toLocaleTimeString()})`}
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

export default memo(CameraStreamOutput);