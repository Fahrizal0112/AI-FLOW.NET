import cv2
import base64
import logging
import time
import sys
import threading
from ..core.processor_type_name_utils import ProcessorType
from .extension_processor import ContextAwareExtensionProcessor
from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig
# Import shared camera untuk konsistensi
from ....flask.routes_camera_stream import _SharedCamera


class CameraInputProcessor(ContextAwareExtensionProcessor):
    """
    Streaming-friendly camera node.

    - stream_mode = 0 → single shot: open, read, return [b64], release
    - stream_mode = 1 → streaming: background thread keeps grabbing frames,
      process() returns the latest frame; will wait up to init_timeout_ms for first frame,
      and if still none, it grabs one synchronous seed frame.

    Output: list[str] berisi base64 JPEG murni (tanpa data URI) atau stream URL.
    """
    processor_type = ProcessorType.CAMERA_INPUT.value

    # Shared runtime state (per instance)
    _shared_cam = None
    _stream_thread = None
    _stop_event = None
    _latest_b64 = None
    _lock = None

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        
        # Helper function to safely parse integer values
        def safe_int(value, default):
            try:
                if isinstance(value, str):
                    # Remove any non-numeric characters except minus sign
                    cleaned = ''.join(c for c in value if c.isdigit() or c == '-')
                    if cleaned and cleaned != '-':
                        return int(cleaned)
                return int(value) if value else default
            except (ValueError, TypeError):
                logging.warning(f"Invalid integer value '{value}', using default {default}")
                return default
        
        def safe_float(value, default):
            try:
                return float(value) if value else default
            except (ValueError, TypeError):
                logging.warning(f"Invalid float value '{value}', using default {default}")
                return default
        
        # Config with validation
        self.camera_index = safe_int(config.get("camera_index", 0), 0)
        self.resolution_width = safe_int(config.get("resolution_width", 640), 640)
        self.resolution_height = safe_int(config.get("resolution_height", 480), 480)
        self.jpeg_quality = safe_int(config.get("jpeg_quality", 85), 85)
        self.read_attempts = safe_int(config.get("read_attempts", 5), 5)
        self.warmup_ms = safe_int(config.get("warmup_ms", 150), 150)
        self.stream_mode = safe_int(config.get("stream_mode", 1), 1)  # default streaming
        self.target_fps = safe_float(config.get("target_fps", 15), 15.0)
        self.init_timeout_ms = safe_int(config.get("init_timeout_ms", 1500), 1500)  # tunggu frame pertama
        self.output_type = config.get("output_type", "videoStream")  # default to video stream

        # Validate ranges
        self.resolution_width = max(160, min(1920, self.resolution_width))
        self.resolution_height = max(120, min(1080, self.resolution_height))
        self.jpeg_quality = max(1, min(100, self.jpeg_quality))
        self.target_fps = max(1.0, min(60.0, self.target_fps))

        # Internals
        if self._lock is None:
            self._lock = threading.Lock()
        
        if self._stop_event is None:
            self._stop_event = threading.Event()
        
        # Initialize shared camera
        self._shared_cam = _SharedCamera(
            index=self.camera_index,
            width=self.resolution_width,
            height=self.resolution_height,
            backend=None
        )

    # ---------------- Helpers ----------------

    def _encode_frame_to_base64(self, frame):
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ok:
            raise Exception("Failed to encode image to JPEG")
        return base64.b64encode(buf).decode("utf-8")

    def _stream_loop(self):
        """Background thread untuk streaming mode dengan shared camera"""
        logging.info("[CameraInput] Stream thread started")
        frame_interval = 1.0 / max(1.0, self.target_fps)
        consecutive_failures = 0
        max_failures = 10
        
        try:
            # Start shared camera
            self._shared_cam.start(fps=self.target_fps, jpeg_quality=self.jpeg_quality)
            
            while not self._stop_event.is_set():
                try:
                    # Get latest JPEG from shared camera
                    jpeg_bytes = self._shared_cam.get_latest_jpeg()
                    
                    if jpeg_bytes is not None:
                        # Convert JPEG bytes to base64
                        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
                        with self._lock:
                            self._latest_b64 = b64
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            logging.error("[CameraInput] Too many consecutive failures, stopping stream")
                            break
                        
                except Exception as e:
                    logging.error(f"[CameraInput] Stream thread error: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.error("[CameraInput] Too many exceptions, stopping stream")
                        break
                
                time.sleep(frame_interval)
                
        except Exception as e:
            logging.error(f"[CameraInput] Stream thread error: {e}")
        finally:
            logging.info("[CameraInput] Stream thread exiting")

    def _start_stream_if_needed(self):
        if self._stream_thread and self._stream_thread.is_alive():
            return
        
        logging.info("[CameraInput] Starting stream thread...")
        self._stop_event.clear()
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def _stop_stream(self):
        logging.info("[CameraInput] Stopping stream thread...")
        self._stop_event.set()
        
        if self._stream_thread:
            self._stream_thread.join(timeout=1.5)
            if self._stream_thread.is_alive():
                logging.warning("[CameraInput] Stream thread did not stop gracefully")
        
        self._stream_thread = None

    def _release_camera(self):
        # Stop shared camera if no other users
        if self._shared_cam:
            self._shared_cam.stop()

    # --------------- Main API -----------------

    def process(self):
        """
        Streaming mode:
          - For videoStream output: return MJPEG stream URL
          - For imageBase64 output: return single base64 image
        Single mode:
          - Capture once and return
        """
        # For videoStream output, return MJPEG stream URL for real-time streaming
        if self.output_type == "videoStream":
            logging.info("[CameraInput] videoStream mode - returning MJPEG stream URL")
            try:
                # Ensure shared camera is started
                self._shared_cam.start(fps=self.target_fps, jpeg_quality=self.jpeg_quality)
                
                # Wait for camera to be ready
                deadline = time.time() + (self.init_timeout_ms / 1000.0)
                while time.time() < deadline:
                    jpeg_bytes = self._shared_cam.get_latest_jpeg()
                    if jpeg_bytes:
                        # Return MJPEG stream URL for real-time streaming
                        stream_url = f"http://localhost:5001/camera/{self.camera_index}.mjpg?w={self.resolution_width}&h={self.resolution_height}&fps={self.target_fps}&q={self.jpeg_quality}"
                        logging.info(f"[CameraInput] Returning stream URL: {stream_url}")
                        return [stream_url]
                    time.sleep(0.03)
                
                # Fallback: try direct capture to test camera
                logging.warning("[CameraInput] No frame from shared camera, testing direct capture")
                cap = cv2.VideoCapture(self.camera_index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        # Camera works, return stream URL
                        stream_url = f"http://localhost:5001/camera/{self.camera_index}.mjpg?w={self.resolution_width}&h={self.resolution_height}&fps={self.target_fps}&q={self.jpeg_quality}"
                        return [stream_url]
                
                logging.error("[CameraInput] Failed to access camera")
                return ["data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIwIiBoZWlnaHQ9IjI0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjY2NjIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg=="]
                
            except Exception as e:
                logging.error(f"[CameraInput] Error in videoStream mode: {e}")
                return ["data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIwIiBoZWlnaHQ9IjI0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjY2NjIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBFcnJvcjwvdGV4dD48L3N2Zz4="]
        
        try:
            # For imageBase64 output - single frame or streaming base64
            if self.stream_mode == 1:
                logging.info("[CameraInput] imageBase64 streaming mode")
                self._start_stream_if_needed()
        
                # Wait for first frame up to init_timeout_ms
                deadline = time.time() + (self.init_timeout_ms / 1000.0)
                latest = None
                while time.time() < deadline:
                    with self._lock:
                        latest = self._latest_b64
                    if latest:
                        return [latest]
                    time.sleep(0.03)
        
                # Still no frame → try to get from shared camera directly
                logging.info("[CameraInput] No frame yet; trying direct capture...")
                try:
                    self._shared_cam.start(fps=self.target_fps, jpeg_quality=self.jpeg_quality)
                    # Wait a bit for camera to initialize
                    time.sleep(0.2)
                    jpeg_bytes = self._shared_cam.get_latest_jpeg()
                    if jpeg_bytes:
                        seed_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
                        with self._lock:
                            self._latest_b64 = seed_b64
                        return [seed_b64]
                    else:
                        raise Exception("No frame available from shared camera")
                except Exception as e:
                    raise Exception(f"Camera not ready: {e}")
            else:
                # --- Single shot using shared camera ---
                logging.info(f"[CameraInput] Single-shot mode using camera index={self.camera_index}")
                try:
                    self._shared_cam.start(fps=15, jpeg_quality=self.jpeg_quality)
                    # Wait for camera to be ready
                    deadline = time.time() + 2.0
                    while time.time() < deadline:
                        jpeg_bytes = self._shared_cam.get_latest_jpeg()
                        if jpeg_bytes:
                            b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
                            logging.info("[CameraInput] Single-shot capture successful")
                            return [b64]
                        time.sleep(0.05)
                    
                    raise Exception("Failed to capture frame in single-shot mode")
                except Exception as e:
                    logging.error(f"[CameraInput] Single-shot error: {e}")
                    raise
        
        except Exception as e:
            logging.error(f"[CameraInput] Error: {e}")
            raise

    def cancel(self):
        logging.info("[CameraInput] cancel(): stopping stream & releasing camera")
        self._stop_stream()
        self._release_camera()

    def get_node_config(self):
        return NodeConfig(
            name="Camera Input (Streaming)",
            description="Capture images from camera with streaming support",
            fields=[
                Field(name="camera_index", label="Camera Index", type="inputInt",
                      required=False, defaultValue=0,
                      description="Camera device index (0 for default camera)."),
                Field(name="resolution_width", label="Width", type="inputInt",
                      required=False, defaultValue=640,
                      description="Camera resolution width."),
                Field(name="resolution_height", label="Height", type="inputInt",
                      required=False, defaultValue=480,
                      description="Camera resolution height."),
                Field(name="jpeg_quality", label="JPEG Quality", type="inputInt",
                      required=False, defaultValue=85,
                      description="JPEG compression quality (1-100)."),
                Field(name="read_attempts", label="Read Attempts", type="inputInt",
                      required=False, defaultValue=5,
                      description="Number of frame read attempts."),
                Field(name="warmup_ms", label="Warmup (ms)", type="inputInt",
                      required=False, defaultValue=150,
                      description="Camera warmup time in milliseconds."),
                Field(name="stream_mode", label="Stream Mode", type="select",
                      required=False, defaultValue=1,
                      options=[{"label": "Single Shot", "value": 0},
                               {"label": "Streaming", "value": 1}],
                      description="Camera capture mode."),
                Field(name="target_fps", label="Target FPS", type="inputFloat",
                      required=False, defaultValue=15.0,
                      description="Approximate FPS while streaming."),
                Field(name="init_timeout_ms", label="Init Timeout (ms)", type="inputInt",
                      required=False, defaultValue=1500,
                      description="Max wait time for first frame in streaming mode."),
                Field(name="output_type", label="Output Type", type="select",
                      required=False, defaultValue="videoStream",
                      options=[{"label": "Video Stream (MJPEG)", "value": "videoStream"},
                               {"label": "Base64 Image", "value": "imageBase64"}],
                      description="Choose between live video stream or base64 image output."),
            ],
            # Set outputType based on the output_type configuration
            outputType="videoStream" if self.output_type == "videoStream" else "imageBase64"
        )
