import json
import base64
from PIL import Image, ImageDraw
import numpy as np
from io import BytesIO
from ..core.processor_type_name_utils import ProcessorType
from .extension_processor import ContextAwareExtensionProcessor
from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig


class ColorVisualizationProcessor(ContextAwareExtensionProcessor):
    processor_type = ProcessorType.COLOR_VISUALIZATION.value

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        self.data_input = config.get("data_input", "")
        self.visualization_type = config.get("visualization_type", "bar_chart")
        self.width = config.get("width", 800)
        self.height = config.get("height", 400)
        self.color_scheme = config.get("color_scheme", "rainbow")

    def process(self):
        """Create color visualization from input data"""
        try:
            # Parse input data
            if isinstance(self.data_input, str):
                try:
                    data = json.loads(self.data_input)
                except:
                    # If not JSON, treat as comma-separated values
                    data = [float(x.strip()) for x in self.data_input.split(',') if x.strip()]
            else:
                data = self.data_input
            
            if not data:
                raise Exception("No data provided for visualization")
            
            # Create visualization
            img = Image.new('RGB', (self.width, self.height), 'white')
            draw = ImageDraw.Draw(img)
            
            if self.visualization_type == "bar_chart":
                self._draw_bar_chart(draw, data)
            elif self.visualization_type == "color_gradient":
                self._draw_color_gradient(draw, data)
            elif self.visualization_type == "heatmap":
                self._draw_heatmap(img, data)
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            raise Exception(f"Color visualization error: {str(e)}")
    
    def _draw_bar_chart(self, draw, data):
        """Draw bar chart visualization"""
        max_val = max(data) if data else 1
        bar_width = self.width // len(data)
        
        for i, value in enumerate(data):
            bar_height = int((value / max_val) * (self.height - 40))
            x1 = i * bar_width
            y1 = self.height - bar_height - 20
            x2 = x1 + bar_width - 2
            y2 = self.height - 20
            
            # Generate color based on value
            color = self._get_color(value, max_val)
            draw.rectangle([x1, y1, x2, y2], fill=color)
    
    def _draw_color_gradient(self, draw, data):
        """Draw color gradient visualization"""
        segment_width = self.width // len(data)
        
        for i, value in enumerate(data):
            x1 = i * segment_width
            x2 = x1 + segment_width
            color = self._get_color(value, max(data))
            draw.rectangle([x1, 0, x2, self.height], fill=color)
    
    def _draw_heatmap(self, img, data):
        """Draw heatmap visualization"""
        # Convert data to 2D array if needed
        if isinstance(data[0], (list, tuple)):
            grid = data
        else:
            # Create square grid from 1D data
            size = int(np.sqrt(len(data)))
            grid = np.array(data[:size*size]).reshape(size, size)
        
        # Create heatmap
        max_val = np.max(grid)
        cell_width = self.width // len(grid[0])
        cell_height = self.height // len(grid)
        
        draw = ImageDraw.Draw(img)
        for i, row in enumerate(grid):
            for j, value in enumerate(row):
                x1 = j * cell_width
                y1 = i * cell_height
                x2 = x1 + cell_width
                y2 = y1 + cell_height
                
                color = self._get_color(value, max_val)
                draw.rectangle([x1, y1, x2, y2], fill=color)
    
    def _get_color(self, value, max_val):
        """Generate color based on value and color scheme"""
        if max_val == 0:
            ratio = 0
        else:
            ratio = value / max_val
        
        if self.color_scheme == "rainbow":
            # HSV to RGB conversion for rainbow colors
            hue = ratio * 300  # 0 to 300 degrees (red to blue)
            return self._hsv_to_rgb(hue, 1.0, 1.0)
        elif self.color_scheme == "heat":
            # Heat map colors (blue to red)
            if ratio < 0.5:
                return (0, int(255 * ratio * 2), 255)
            else:
                return (int(255 * (ratio - 0.5) * 2), 255, int(255 * (1 - ratio) * 2))
        else:
            # Default grayscale
            gray = int(255 * ratio)
            return (gray, gray, gray)
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB"""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h/360, s, v)
        return (int(r*255), int(g*255), int(b*255))

    def get_node_config(self):
        data_input_field = Field(
            name="data_input",
            label="Data Input",
            type="textarea",
            required=True,
            placeholder="Enter data as JSON array or comma-separated values",
            description="Data to visualize (JSON array or comma-separated numbers)"
        )
        
        visualization_type_field = Field(
            name="visualization_type",
            label="Visualization Type",
            type="select",
            required=True,
            defaultValue="bar_chart",
            options=[
                {"label": "Bar Chart", "value": "bar_chart"},
                {"label": "Color Gradient", "value": "color_gradient"},
                {"label": "Heatmap", "value": "heatmap"}
            ],
            description="Type of color visualization"
        )
        
        width_field = Field(
            name="width",
            label="Width",
            type="inputInt",
            required=False,
            defaultValue=800,
            description="Image width in pixels"
        )
        
        height_field = Field(
            name="height",
            label="Height",
            type="inputInt",
            required=False,
            defaultValue=400,
            description="Image height in pixels"
        )
        
        color_scheme_field = Field(
            name="color_scheme",
            label="Color Scheme",
            type="select",
            required=False,
            defaultValue="rainbow",
            options=[
                {"label": "Rainbow", "value": "rainbow"},
                {"label": "Heat Map", "value": "heat"},
                {"label": "Grayscale", "value": "grayscale"}
            ],
            description="Color scheme for visualization"
        )

        return NodeConfig(
            processorType=self.processor_type,
            nodeName="Color Visualization",
            icon="AiOutlineBarChart",
            section="tools",
            outputType="imageBase64",
            defaultHideOutput=False,
            fields=[data_input_field, visualization_type_field, width_field, height_field, color_scheme_field]
        )

    def cancel(self):
        pass