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


class CameraInputProcessor(ContextAwareExtensionProcessor):
    """
    Streaming-friendly camera node.

    - stream_mode = 0 → single shot: open, read, return [b64], release
    - stream_mode = 1 → streaming: background thread keeps grabbing frames,
      process() returns the latest frame; will wait up to init_timeout_ms for first frame,
      and if still none, it grabs one synchronous seed frame.

    Output: list[str] berisi base64 JPEG murni (tanpa data URI).
    """
    processor_type = ProcessorType.CAMERA_INPUT.value

    # Shared runtime state (per instance)
    _cap = None
    _stream_thread = None
    _stop_event = None
    _latest_b64 = None
    _lock = None

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        # Config
        self.camera_index = int(config.get("camera_index", 0))
        self.resolution_width = int(config.get("resolution_width", 640))
        self.resolution_height = int(config.get("resolution_height", 480))
        self.jpeg_quality = int(config.get("jpeg_quality", 85))
        self.read_attempts = int(config.get("read_attempts", 5))
        self.warmup_ms = int(config.get("warmup_ms", 150))
        self.stream_mode = int(config.get("stream_mode", 1))  # default streaming
        self.target_fps = float(config.get("target_fps", 15))
        self.init_timeout_ms = int(config.get("init_timeout_ms", 1500))  # tunggu frame pertama
        self.output_type = config.get("output_type", "videoStream")  # default to video stream

        # Internals
        if self._lock is None:
            self._lock = threading.Lock()

    # ---------------- Helpers ----------------

    def _open_capture(self):
        """Open cv2.VideoCapture with appropriate backend per OS."""
        if sys.platform == "darwin":
            # Try AVFoundation first, then fallback to default
            backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        elif sys.platform.startswith("win"):
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
        
        for backend in backends:
            try:
                logging.info(f"[CameraInput] Trying backend: {backend} for camera {self.camera_index}")
                cap = cv2.VideoCapture(self.camera_index, backend)
                if cap and cap.isOpened():
                    # Test if we can actually read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        logging.info(f"[CameraInput] Successfully opened camera {self.camera_index} with backend {backend}")
                        return cap
                    else:
                        logging.warning(f"[CameraInput] Camera opened but cannot read frame with backend {backend}")
                        cap.release()
                else:
                    logging.warning(f"[CameraInput] Failed to open camera {self.camera_index} with backend {backend}")
                    if cap:
                        cap.release()
            except Exception as e:
                logging.error(f"[CameraInput] Exception with backend {backend}: {e}")
                
        raise Exception(
            f"Cannot open camera {self.camera_index} with any backend. "
            f"Please check: 1) Camera is connected, 2) No other app is using it, "
            f"3) Camera permissions are granted in System Preferences > Security & Privacy > Camera"
        )

    def _setup_resolution(self, cap):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution_height)

    def _encode_frame_to_base64(self, frame):
        ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ok:
            raise Exception("Failed to encode image to JPEG")
        return base64.b64encode(buffer.tobytes()).decode('utf-8')  # PURE BASE64

    # -------------- Streaming core ------------

    def _ensure_camera_open(self):
        """Open and warm up the camera if not already open."""
        if self._cap is not None and self._cap.isOpened():
            # Test if camera is still working
            ret, frame = self._cap.read()
            if ret and frame is not None:
                return
            else:
                logging.warning("[CameraInput] Camera connection lost, reopening...")
                self._cap.release()
                self._cap = None
        
        self._cap = self._open_capture()
        self._setup_resolution(self._cap)
        time.sleep(self.warmup_ms / 1000.0)
        
        # Verify camera is working after setup
        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise Exception(
                f"Camera {self.camera_index} opened but cannot capture frames. "
                f"Try a different camera index or check camera permissions."
            )
        logging.info(f"[CameraInput] Camera {self.camera_index} ready and verified")

    def _stream_loop(self):
        logging.info("[CameraInput] Stream thread started")
        frame_interval = 1.0 / max(1.0, self.target_fps)
        consecutive_failures = 0
        max_failures = 10
        
        try:
            self._ensure_camera_open()
            while not self._stop_event.is_set():
                # Check if camera is still valid before reading
                if self._cap is None or not self._cap.isOpened():
                    logging.warning("[CameraInput] Camera not available, attempting to reopen...")
                    try:
                        self._ensure_camera_open()
                    except Exception as e:
                        logging.error(f"[CameraInput] Failed to reopen camera: {e}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            logging.error("[CameraInput] Too many consecutive failures, stopping stream")
                            break
                        time.sleep(1.0)  # Wait longer before retry
                        continue
                
                # Only try to read if camera is available
                if self._cap and self._cap.isOpened():
                    try:
                        ret, frame = self._cap.read()
                        if not ret or frame is None:
                            consecutive_failures += 1
                            logging.warning(f"[CameraInput] Failed to read frame (attempt {consecutive_failures})")
                            
                            # Try soft recover
                            recovered = False
                            for retry in range(3):
                                time.sleep(0.05)
                                if self._cap and self._cap.isOpened():
                                    ret, frame = self._cap.read()
                                    if ret and frame is not None:
                                        recovered = True
                                        consecutive_failures = 0  # Reset failure count
                                        break
                            
                            if not recovered:
                                if consecutive_failures >= max_failures:
                                    logging.error("[CameraInput] Too many consecutive read failures, stopping stream")
                                    break
                                    
                                logging.warning("[CameraInput] Lost frame; reopening camera...")
                                try:
                                    if self._cap:
                                        self._cap.release()
                                    self._cap = None
                                    self._ensure_camera_open()
                                    # Don't immediately try to read, let the next loop iteration handle it
                                    time.sleep(frame_interval)
                                    continue
                                except Exception as ee:
                                    logging.error(f"[CameraInput] Reopen failed: {ee}")
                                    consecutive_failures += 1
                                    time.sleep(1.0)  # Wait longer after reopen failure
                                    continue
                        else:
                            # Successfully read frame, reset failure count
                            consecutive_failures = 0
                            
                            try:
                                b64 = self._encode_frame_to_base64(frame)
                                with self._lock:
                                    self._latest_b64 = b64
                            except Exception as enc_e:
                                logging.error(f"[CameraInput] Encode error: {enc_e}")
                                
                    except Exception as read_e:
                        logging.error(f"[CameraInput] Read exception: {read_e}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            logging.error("[CameraInput] Too many exceptions, stopping stream")
                            break
                        time.sleep(0.5)
                        continue
                else:
                    # Camera not available, wait and continue
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logging.error("[CameraInput] Camera unavailable for too long, stopping stream")
                        break
                    time.sleep(1.0)
                    continue
    
                time.sleep(frame_interval)
    
        except Exception as e:
            logging.error(f"[CameraInput] Stream thread error: {e}")
        finally:
            logging.info("[CameraInput] Stream thread exiting")
            # Clean up camera on exit
            if self._cap:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None

    def _start_stream_if_needed(self):
        if self._stream_thread and self._stream_thread.is_alive():
            return
        # reset latest frame state
        with self._lock:
            self._latest_b64 = None
        self._stop_event = threading.Event()
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def _stop_stream(self):
        try:
            if self._stop_event:
                self._stop_event.set()
            if self._stream_thread:
                self._stream_thread.join(timeout=1.5)
        except Exception:
            pass
        finally:
            self._stream_thread = None
            self._stop_event = None

    def _release_camera(self):
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    # --------------- Main API -----------------

    def process(self):
        """
        Streaming mode:
          - Start stream thread if needed
          - Wait up to init_timeout_ms for first frame
          - If still none, grab 1 seed frame synchronously, set latest, return it
        Single mode:
          - Capture once and return
        """
        # Return MJPEG stream URL if output_type is videoStream
        if self.output_type == "videoStream":
            stream_url = f"http://localhost:5000/camera/{self.camera_index}.mjpg"
            return [stream_url]
        
        # Initialize cap_local at the beginning to avoid scope issues
        cap_local = None
        
        try:
            # Original behavior for imageBase64 output
            if self.stream_mode == 1:
                logging.info("[CameraInput] process() streaming mode")
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
        
                # Still no frame → seed synchronously (rare, but safe)
                logging.info("[CameraInput] No frame yet; doing synchronous seed capture...")
                try:
                    self._ensure_camera_open()
                    ok, frame = self._cap.read()
                    if ok and frame is not None:
                        seed_b64 = self._encode_frame_to_base64(frame)
                        with self._lock:
                            self._latest_b64 = seed_b64
                        return [seed_b64]
                    else:
                        raise Exception("Seed capture failed")
                except Exception as e:
                    # Jangan spam UI dengan error; beri pesan singkat yang actionable
                    raise Exception(f"Camera not ready (seed failed): {e}")
            else:
                # --- Single shot ---
                logging.info(f"[CameraInput] Opening camera index={self.camera_index} (single-shot)")
                try:
                    cap_local = self._open_capture()
                    if not cap_local or not cap_local.isOpened():
                        raise Exception(
                            f"Cannot open camera {self.camera_index}. "
                            f"Run on the same machine, grant permissions, and use the right backend."
                        )
                    self._setup_resolution(cap_local)
                    time.sleep(self.warmup_ms / 1000.0)
            
                    ok, frame = cap_local.read()
                    if not ok or frame is None:
                        # retry a few times
                        for _ in range(max(1, self.read_attempts) - 1):
                            time.sleep(0.03)
                            ok, frame = cap_local.read()
                            if ok and frame is not None:
                                break
                        if not ok or frame is None:
                            raise Exception("Failed to capture frame after multiple attempts")
            
                    b64 = self._encode_frame_to_base64(frame)
                    logging.info("[CameraInput] Single-shot capture successful")
                    return [b64]
                except Exception as e:
                    logging.error(f"[CameraInput] Single-shot error: {e}")
                    raise
        
        except Exception as e:
            logging.error(f"[CameraInput] Error: {e}")
            raise
        finally:
            if cap_local is not None:
                try:
                    cap_local.release()
                except Exception:
                    pass

    def cancel(self):
        """Called when the node/flow is stopped."""
        logging.info("[CameraInput] cancel(): stopping stream & releasing camera")
        self._stop_stream()
        self._release_camera()

    def get_node_config(self):
        # Dynamic output type based on configuration
        output_type = getattr(self, 'output_type', 'videoStream')
        return NodeConfig(
            processorType=self.processor_type,
            nodeName="Camera Input (Streaming)",
            icon="AiOutlineCamera",
            section="input",
            outputType=output_type,
            defaultHideOutput=False,
            fields=[
                Field(name="camera_index", label="Camera Index", type="inputInt",
                      required=False, defaultValue=0,
                      description="Index of camera device (0 default, 1 external)."),
                Field(name="resolution_width", label="Width", type="inputInt",
                      required=False, defaultValue=640,
                      description="Camera resolution width in pixels."),
                Field(name="resolution_height", label="Height", type="inputInt",
                      required=False, defaultValue=480,
                      description="Camera resolution height in pixels."),
                Field(name="jpeg_quality", label="JPEG Quality", type="inputInt",
                      required=False, defaultValue=85,
                      description="JPEG quality (1-100)."),
                Field(name="read_attempts", label="Read Attempts", type="inputInt",
                      required=False, defaultValue=5,
                      description="Retries for single-shot mode."),
                Field(name="warmup_ms", label="Warm-up (ms)", type="inputInt",
                      required=False, defaultValue=150,
                      description="Delay before reading frames."),
                Field(name="stream_mode", label="Stream Mode (0/1)", type="inputInt",
                      required=False, defaultValue=1,
                      description="0 = single-shot; 1 = streaming via background thread."),
                Field(name="target_fps", label="Target FPS (stream)", type="inputInt",
                      required=False, defaultValue=15,
                      description="Approximate FPS while streaming."),
                Field(name="init_timeout_ms", label="Init Timeout (ms)", type="inputInt",
                      required=False, defaultValue=1500,
                      description="Max wait for first frame before seeding."),
                Field(name="output_type", label="Output Type", type="select",
                      required=False, defaultValue="videoStream",
                      options=[{"label": "Video Stream (MJPEG)", "value": "videoStream"}, 
                              {"label": "Base64 Images", "value": "imageBase64"}],
                      description="Choose between live video stream or base64 image output."),
            ]
        )
