import React, { memo } from "react";
import { FaDownload } from "react-icons/fa";
import styled from "styled-components";

interface ImageBase64OutputProps {
  data: string;
  name: string;
  lastRun?: string;
}

const ImageBase64Output: React.FC<ImageBase64OutputProps> = ({
  data,
  name,
  lastRun,
}) => {
  // Handle different data formats
  let imageUrl: string;
  let base64Data: string;

  try {
    if (data.startsWith('data:image/')) {
      // Already a data URI, use directly
      imageUrl = data;
      // Extract base64 part for download
      base64Data = data.split(',')[1] || '';
    } else {
      // Raw base64 data, create data URI
      base64Data = data;
      imageUrl = `data:image/jpeg;base64,${data}`;
    }

    // Validate base64 data before using atob
    if (!base64Data || base64Data.length === 0) {
      throw new Error('No base64 data available');
    }

    // Test if base64 is valid
    atob(base64Data);
  } catch (error) {
    console.error('Invalid base64 data:', error);
    return (
      <OutputImageContainer>
        <ErrorMessage>
          Invalid image data
          <br />
          <small>Unable to display image</small>
        </ErrorMessage>
      </OutputImageContainer>
    );
  }

  const handleDownloadClick = () => {
    try {
      const blob = new Blob([
        new Uint8Array(
          atob(base64Data)
            .split("")
            .map(function (c) {
              return c.charCodeAt(0);
            }),
        ),
      ], { type: 'image/jpeg' });

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = name + "-output-generated.jpg";
      link.target = "_blank";
      link.click();
      
      // Clean up the URL after download
      setTimeout(() => URL.revokeObjectURL(url), 100);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <OutputImageContainer>
      <OutputImage src={imageUrl} alt="Output Image" />
      <DownloadButton onClick={handleDownloadClick}>
        <FaDownload />
      </DownloadButton>
    </OutputImageContainer>
  );
};

const OutputImageContainer = styled.div`
  position: relative;
  margin-top: 10px;
`;

const OutputImage = styled.img`
  display: block;
  width: 100%;
  height: auto;
  border-radius: 8px;
`;

const ErrorMessage = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background-color: #f5f5f5;
  border: 2px dashed #ccc;
  border-radius: 8px;
  color: #666;
  text-align: center;
  min-height: 100px;
`;

const DownloadButton = styled.a`
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background-color: #4285f4;
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  transition: background-color 0.3s ease;

  &:hover {
    background-color: #0d47a1;
  }
`;

function arePropsEqual(
  prevProps: ImageBase64OutputProps,
  nextProps: ImageBase64OutputProps,
) {
  return prevProps.lastRun === nextProps.lastRun;
}

export default memo(ImageBase64Output, arePropsEqual);
