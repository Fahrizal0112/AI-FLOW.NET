# packages/backend/app/flask/routes_camera_stream.py
import cv2
import time
import sys
import threading
import base64
from flask import Blueprint, Response, current_app

bp_camera_stream = Blueprint("camera_stream", __name__)

class _SharedCamera:
    """Singleton per camera index, share VideoCapture + thread ke banyak client."""
    _instances = {}
    _global_lock = threading.Lock()

    def __new__(cls, index=0, width=640, height=480, backend=None):
        key = (index, width, height, backend)
        with cls._global_lock:
            if key not in cls._instances:
                obj = super().__new__(cls)
                obj.index = index
                obj.width = width
                obj.height = height
                obj.backend = backend
                obj.cap = None
                obj.frame_lock = threading.Lock()
                obj.latest_jpeg = None  # bytes (JPEG)
                obj.stop_evt = threading.Event()
                obj.thread = None
                cls._instances[key] = obj
            return cls._instances[key]

    def _open(self):
        if sys.platform == "darwin":
            default_backend = cv2.CAP_AVFOUNDATION
        elif sys.platform.startswith("win"):
            default_backend = cv2.CAP_MSMF
        else:
            default_backend = cv2.CAP_V4L2

        backend = self.backend if self.backend is not None else default_backend
        self.cap = cv2.VideoCapture(self.index, backend)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        time.sleep(0.15)  # warm-up

    def _loop(self, fps=15, jpeg_quality=85):
        try:
            self._open()
            interval = 1.0 / max(1.0, fps)
            while not self.stop_evt.is_set():
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    time.sleep(0.03)
                    continue
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                if ok:
                    with self.frame_lock:
                        self.latest_jpeg = buf.tobytes()
                time.sleep(interval)
        except Exception as e:
            current_app.logger.error(f"[CameraStream] loop error: {e}")
        finally:
            if self.cap:
                try: self.cap.release()
                except Exception: pass
            self.cap = None

    def start(self, fps=15, jpeg_quality=85):
        if self.thread and self.thread.is_alive():
            return
        self.stop_evt.clear()
        self.thread = threading.Thread(target=self._loop, args=(fps, jpeg_quality), daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_evt.set()
        if self.thread:
            self.thread.join(timeout=1.5)
        self.thread = None
        if self.cap:
            try: self.cap.release()
            except Exception: pass
        self.cap = None

    def get_latest_jpeg(self):
        with self.frame_lock:
            return self.latest_jpeg


@bp_camera_stream.route("/camera/<int:index>.mjpg")
def stream_mjpeg(index: int):
    """
    Stream MJPEG untuk camera <index>.
    Query param opsional: ?w=640&h=480&fps=15&q=85
    """
    from flask import request

    width = int(request.args.get("w", 640))
    height = int(request.args.get("h", 480))
    fps = float(request.args.get("fps", 15))
    q = int(request.args.get("q", 85))

    cam = _SharedCamera(index=index, width=width, height=height, backend=None)
    cam.start(fps=fps, jpeg_quality=q)

    boundary = "frame"
    def gen():
        # tunggu frame pertama
        deadline = time.time() + 3.0
        while cam.get_latest_jpeg() is None and time.time() < deadline:
            time.sleep(0.03)
        while True:
            jpg = cam.get_latest_jpeg()
            if jpg is None:
                time.sleep(0.01)
                continue
            yield (b"--" + boundary.encode() + b"\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" +
                   jpg + b"\r\n")
    return Response(gen(), mimetype=f"multipart/x-mixed-replace; boundary={boundary}")
