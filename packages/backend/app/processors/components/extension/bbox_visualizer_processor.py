import logging
import json
import os
import tempfile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import colorsys
import requests
import base64
from typing import Dict, Any, List
from datetime import datetime

from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig, Option
from .extension_processor import ContextAwareExtensionProcessor


class BboxVisualizerProcessor(ContextAwareExtensionProcessor):
    processor_type = "bbox-visualizer-processor"
    
    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
    
    def get_node_config(self):
        image_url = Field(
            name="image_url",
            label="Image URL",
            type="textfield",
            required=True,
            placeholder="Enter image URL or upload image",
            hasHandle=True,
        )
        
        detections_data = Field(
            name="detections_data",
            label="Detection Data",
            type="textarea",
            required=True,
            placeholder="Paste YOLO detection JSON data here",
            hasHandle=True,
        )
        
        box_thickness = Field(
            name="box_thickness",
            label="Box Thickness",
            type="numericfield",
            required=False,
            placeholder="3",
            hasHandle=True,
        )
        
        show_labels = Field(
            name="show_labels",
            label="Show Labels",
            type="switch",
            required=False,
            hasHandle=True,
        )
        
        save_to_local = Field(
            name="save_to_local",
            label="Save to Local Storage",
            type="switch",
            required=False,
            hasHandle=True,
        )
        
        output_folder = Field(
            name="output_folder",
            label="Output Folder Name",
            type="textfield",
            required=False,
            placeholder="bbox_results",
            hasHandle=True,
        )
        
        fields = [image_url, detections_data, box_thickness, show_labels, save_to_local, output_folder]
        
        config = NodeConfig(
            nodeName="Bounding Box Visualizer",
            processorType=self.processor_type,
            icon="ViewfinderCircleIcon",
            fields=fields,
            outputType="imageBase64",
            section="tools",
            helpMessage="bboxVisualizerHelp",
            showHandlesNames=True,
        )
        
        return config
    
    def load_image_from_url(self, url: str) -> Image.Image:
        """Load image from URL or local path"""
        try:
            if url.startswith('http'):
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '').lower()
                if not content_type.startswith('image/'):
                    if len(response.content) < 100:
                        raise Exception(f"Response too small ({len(response.content)} bytes), likely not an image")
                
                if len(response.content) == 0:
                    raise Exception("Empty response content")
                    
                # Load image from response content
                image_data = BytesIO(response.content)
                image = Image.open(image_data)
                
                # Convert to RGB if necessary (for PNG with transparency)
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                    
            else:
                # Load from local path
                image = Image.open(url)
                
                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
            
            logging.info(f"Successfully loaded image: {image.size}, mode: {image.mode}")
            return image
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch image from URL: {str(e)}")
            raise Exception(f"Failed to fetch image from URL: {str(e)}")
        except Image.UnidentifiedImageError as e:
            logging.error(f"Invalid image format or corrupted image: {str(e)}")
            raise Exception(f"Invalid image format or corrupted image: {str(e)}")
        except Exception as e:
            logging.error(f"Failed to load image: {str(e)}")
            raise Exception(f"Failed to load image: {str(e)}")
    
    def generate_colors(self, num_colors: int) -> List[tuple]:
        """Generate distinct colors for bounding boxes"""
        colors = []
        for i in range(num_colors):
            hue = i / num_colors
            saturation = 0.8
            value = 0.9
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            colors.append(tuple(int(c * 255) for c in rgb))
        return colors
    
    def draw_bounding_boxes(self, image: Image.Image, detections: List[Dict], 
                          box_thickness: int = 3, show_labels: bool = True) -> Image.Image:
        """Draw bounding boxes on image"""
        draw_image = image.copy()
        draw = ImageDraw.Draw(draw_image)
        
        # Get unique class names for color assignment
        class_names = list(set([det['class'] for det in detections]))
        colors = self.generate_colors(len(class_names))
        class_colors = {class_name: colors[i % len(colors)] for i, class_name in enumerate(class_names)}
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
        
        for detection in detections:
            bbox = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            color = class_colors[class_name]
            
            # Draw bounding box
            x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
            for i in range(box_thickness):
                draw.rectangle(
                    [x1 - i, y1 - i, x2 + i, y2 + i],
                    outline=color,
                    width=1
                )
            
            # Draw label if requested
            if show_labels:
                label = f"{class_name}: {confidence:.2f}"
                
                # Get text bounding box
                bbox_text = draw.textbbox((0, 0), label, font=font)
                text_width = bbox_text[2] - bbox_text[0]
                text_height = bbox_text[3] - bbox_text[1]
                
                # Draw label background
                label_bg = [x1, y1 - text_height - 4, x1 + text_width + 4, y1]
                draw.rectangle(label_bg, fill=color)
                
                # Draw label text
                draw.text((x1 + 2, y1 - text_height - 2), label, fill=(255, 255, 255), font=font)
        
        return draw_image
    
    def save_image_to_local(self, image: Image.Image, folder_name: str = "bbox_results") -> str:
        """Save image to local storage and return the file path"""
        try:
            # Create output directory in the project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            output_dir = os.path.join(project_root, "output", folder_name)
            
            # Create directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bbox_result_{timestamp}.png"
            file_path = os.path.join(output_dir, filename)
            
            # Save image
            image.save(file_path, "PNG")
            
            logging.info(f"Image saved to: {file_path}")
            return file_path
            
        except Exception as e:
            logging.error(f"Failed to save image to local storage: {str(e)}")
            raise Exception(f"Failed to save image to local storage: {str(e)}")
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        # Return only the base64 string without data URI prefix for imageBase64 output type
        return image_base64
    
    def process(self):
        image_url = self.get_input_by_name("image_url")
        detections_data = self.get_input_by_name("detections_data")
        box_thickness = int(self.get_input_by_name("box_thickness", "3"))
        show_labels = self.get_input_by_name("show_labels", True)
        save_to_local = self.get_input_by_name("save_to_local", False)
        output_folder = self.get_input_by_name("output_folder", "bbox_results")
        
        if not image_url:
            raise Exception("Image URL is required")
        
        if not detections_data:
            raise Exception("Detection data is required")
        
        try:
            # Add debugging
            logging.info(f"Received detections_data type: {type(detections_data)}")
            logging.info(f"Detections_data content: {str(detections_data)[:200]}...")
            
            # Parse detection data
            if isinstance(detections_data, str):
                detection_json = json.loads(detections_data)
            else:
                detection_json = detections_data
            
            detections = detection_json.get('detections', [])
            
            if not detections:
                raise Exception("No detections found in the provided data")
            
            # Validate detection format
            for i, detection in enumerate(detections):
                if 'bbox' not in detection:
                    raise Exception(f"Detection {i} missing 'bbox' field")
                bbox = detection['bbox']
                required_keys = ['x1', 'y1', 'x2', 'y2']
                for key in required_keys:
                    if key not in bbox:
                        raise Exception(f"Detection {i} bbox missing '{key}' coordinate")
            
            # Load image
            image = self.load_image_from_url(image_url)
            logging.info(f"Loaded image size: {image.size}, mode: {image.mode}")
            
            # Draw bounding boxes
            result_image = self.draw_bounding_boxes(
                image, detections, box_thickness, show_labels
            )
            logging.info(f"Result image size: {result_image.size}, mode: {result_image.mode}")
            
            # Save to local storage if requested
            if save_to_local:
                saved_path = self.save_image_to_local(result_image, output_folder)
                logging.info(f"Image saved to local storage: {saved_path}")
            
            # Convert image to base64 string for output
            image_base64 = self.image_to_base64(result_image)
            logging.info(f"Generated base64 string length: {len(image_base64)}")
            
            # Return the base64 string (for imageBase64 output type)
            return image_base64
            
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in detection data: {str(e)}")
            raise Exception(f"Invalid JSON in detection data: {str(e)}")
        except Exception as e:
            logging.error(f"Bounding box visualization failed: {str(e)}")
            raise Exception(f"Bounding box visualization failed: {str(e)}")
    
    def cancel(self):
        pass