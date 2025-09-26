import logging
import json
from ultralytics import YOLO
from PIL import Image
import requests
from io import BytesIO

from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig, Option
from .extension_processor import ContextAwareExtensionProcessor


class YOLODetectionProcessor(ContextAwareExtensionProcessor):
    processor_type = "yolo-detection-processor"
    
    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        self.model = None
    
    def get_node_config(self):
        image_url = Field(
            name="image_url",
            label="Image URL",
            type="textfield",
            required=True,
            placeholder="Enter image URL or upload image",
            hasHandle=True,
        )
        
        model_options = [
            Option(
                default=True,
                value="yolov8n.pt",
                label="YOLOv8 Nano (Fast)",
            ),
            Option(
                default=False,
                value="yolov8s.pt",
                label="YOLOv8 Small",
            ),
            Option(
                default=False,
                value="yolov8m.pt",
                label="YOLOv8 Medium",
            ),
            Option(
                default=False,
                value="yolov8l.pt",
                label="YOLOv8 Large",
            ),
            Option(
                default=False,
                value="yolov8x.pt",
                label="YOLOv8 Extra Large (Accurate)",
            ),
        ]
        
        model_field = Field(
            name="model",
            label="YOLO Model",
            type="select",
            options=model_options,
            required=True,
        )
        
        confidence = Field(
            name="confidence",
            label="Confidence Threshold",
            type="numericfield",
            required=False,
            placeholder="0.5",
            hasHandle=True,
        )
        
        fields = [image_url, model_field, confidence]
        
        config = NodeConfig(
            nodeName="YOLO Object Detection",
            processorType=self.processor_type,
            icon="EyeIcon",
            fields=fields,
            outputType="text",
            section="tools",
            helpMessage="yoloDetectionHelp",
            showHandlesNames=True,
        )
        
        return config
    
    def load_image_from_url(self, url):
        """Load image from URL or local path"""
        try:
            if url.startswith('http'):
                # Add proper headers to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Check if content is actually an image
                content_type = response.headers.get('content-type', '').lower()
                if not content_type.startswith('image/'):
                    # Try to detect if it's still an image by checking content
                    if len(response.content) < 100:
                        raise Exception(f"Response too small ({len(response.content)} bytes), likely not an image")
                
                # Validate content before creating BytesIO
                if len(response.content) == 0:
                    raise Exception("Empty response content")
                    
                image = Image.open(BytesIO(response.content))
            else:
                # Handle local file path
                image = Image.open(url)
            
            # Verify image was loaded successfully
            image.verify()
            # Reopen image after verify (verify() closes the file)
            if url.startswith('http'):
                image = Image.open(BytesIO(response.content))
            else:
                image = Image.open(url)
                
            return image
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch image from URL: {str(e)}")
        except Image.UnidentifiedImageError as e:
            raise Exception(f"Invalid image format or corrupted image: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to load image: {str(e)}")
    
    def process(self):
        image_url = self.get_input_by_name("image_url")
        model_name = self.get_input_by_name("model", "yolov8n.pt")
        confidence = float(self.get_input_by_name("confidence", "0.5"))
        
        if not image_url:
            raise Exception("Image URL is required")
        
        try:
            # Load YOLO model
            if not self.model or self.model.model_name != model_name:
                logging.info(f"Loading YOLO model: {model_name}")
                self.model = YOLO(model_name)
                self.model.model_name = model_name
            
            # Load and process image
            image = self.load_image_from_url(image_url)
            
            # Run detection
            results = self.model(image, conf=confidence)
            
            # Process results
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        detection = {
                            "class": result.names[int(box.cls[0])],
                            "confidence": float(box.conf[0]),
                            "bbox": {
                                "x1": float(box.xyxy[0][0]),
                                "y1": float(box.xyxy[0][1]),
                                "x2": float(box.xyxy[0][2]),
                                "y2": float(box.xyxy[0][3]),
                            }
                        }
                        detections.append(detection)
            
            # Format output
            output = {
                "detections": detections,
                "total_objects": len(detections),
                "image_size": {
                    "width": image.width,
                    "height": image.height
                }
            }
            
            return json.dumps(output, indent=2)
            
        except Exception as e:
            logging.error(f"YOLO detection failed: {str(e)}")
            raise Exception(f"YOLO detection failed: {str(e)}")
    
    def cancel(self):
        pass