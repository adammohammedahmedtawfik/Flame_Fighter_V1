from pathlib import Path
import threading, time, os, sys, socket, atexit
import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template
from ultralytics import YOLO
import requests, serial, serial.tools.list_ports

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)

# Model paths
FIRE_MODEL = ROOT / "runs/detect/finetune_v1/weights/best.pt"
SOCKET_MODEL = ROOT / "runs/detect/electric_finetune_v1/weights/best.pt"

# Detection settings
CONF_FIRE = 0.5
CONF_SOCKET = 0.4
IMGSZ = 640

W, H = 640, 480
PORT = 5000
THRESHOLD = 140
SAFETY_MARGIN = 120
PIXEL_TO_CM = 0.026

# Arduino USB Serial connection
arduino_serial = None

def init_arduino_serial():
    global arduino_serial
    try:
        for p in serial.tools.list_ports.comports():
            desc = p.description.lower()
            if "arduino" in desc or "ch340" in desc or "usb serial" in desc or "vid:pid=2341" in p.hwid.lower():
                arduino_serial = serial.Serial(p.device, 9600, timeout=1)
                time.sleep(1.5)
                print(f"âœ… [ARDUINO USB] Connected on {p.device} ({p.description})")
                return
        for p in serial.tools.list_ports.comports():
            if "bluetooth" not in p.description.lower():
                arduino_serial = serial.Serial(p.device, 9600, timeout=1)
                time.sleep(1.5)
                print(f"âœ… [ARDUINO USB] Connected on fallback {p.device}")
                return
        print("âš ï¸ [ARDUINO USB] No Arduino COM port found.")
    except Exception as e:
        print(f"âš ï¸ [ARDUINO USB] Connection failed: {e}")
        arduino_serial = None

init_arduino_serial()

# RPi fallback (if Arduino USB unavailable)
RASPBERRY_IP = "10.204.175.235"
RASPBERRY_PORT = 5001

last_sent_decision = None

def _send_command(cmd):
    global arduino_serial
    if not (arduino_serial and arduino_serial.is_open):
        init_arduino_serial()

    # Primary: direct USB serial
    if arduino_serial and arduino_serial.is_open:
        try:
            arduino_serial.write(f"{cmd}\n".encode())
            print(f"âš¡ [ARDUINO USB] Sent -> {cmd}")
            return
        except Exception as e:
            print(f"âŒ Serial write error: {e}")
            arduino_serial = None

    # Fallback: RPi HTTP bridge
    try:
        url = f"http://{RASPBERRY_IP}:{RASPBERRY_PORT}/command/{cmd}"
        requests.get(url, timeout=0.3)
    except:
        pass

def send_arduino_command(decision):
    global last_sent_decision
    
    cmd_map = {
        "WATER PUMP": "WATER_ON",
        "FOAM PUMP": "FOAM_ON",
        "NO FIRE": "STOP_ALL"
    }
    
    cmd = cmd_map.get(decision, "STOP_ALL")
    
    if cmd != last_sent_decision:
        last_sent_decision = cmd
        threading.Thread(target=_send_command, args=(cmd,), daemon=True).start()

selected_cam_index = 0
selected_cam_label = "Built-in Laptop"

def get_forced_cam_index():
    if "--cam" in sys.argv:
        try:
            return int(sys.argv[sys.argv.index("--cam") + 1])
        except (ValueError, IndexError):
            pass
    return None

def init_camera() -> cv2.VideoCapture:
    """
    Prioritizes USB external camera (indices 1-4).
    Falls back to built-in laptop camera (index 0).
    Uses CAP_DSHOW on Windows for high performance & stability.
    """
    global selected_cam_index, selected_cam_label
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0

    forced = get_forced_cam_index()
    if forced is not None:
        cap = cv2.VideoCapture(forced, backend)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                selected_cam_index = forced
                selected_cam_label = f"Forced Camera (Index {forced})"
                print(f"🎯 [CAM] Using forced camera index: {forced}")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
                return cap
            cap.release()
        print(f"⚠️ [CAM] Forced camera index {forced} failed to open. Scanning automatically...")

    print("🔍 [CAM] Scanning for cameras (prioritizing USB External)...")
    # Priority 1: Check external USB cameras first (indices 1 to 4)
    for index in [1, 2, 3, 4]:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                selected_cam_index = index
                selected_cam_label = f"USB External Camera (Index {index})"
                print(f"✅ [CAM] USB External Camera detected and activated on Index {index}!")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
                return cap
            cap.release()

    # Priority 2: Fallback to built-in laptop camera (index 0)
    print("💻 [CAM] No USB External camera found. Trying Built-in Laptop Camera (Index 0)...")
    cap = cv2.VideoCapture(0, backend)
    if cap.isOpened():
        ok, _ = cap.read()
        if ok:
            selected_cam_index = 0
            selected_cam_label = "Built-in Laptop Camera (Index 0)"
            print("✅ [CAM] Built-in Laptop Camera activated on Index 0.")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
            return cap
        cap.release()

    raise RuntimeError("❌ [CAM] No working camera found. Check connections.")


camera = init_camera()

# Load YOLO models
fire_model = YOLO(str(FIRE_MODEL))
socket_model = YOLO(str(SOCKET_MODEL))

def _create_standby_frame():
    img = np.zeros((H, W, 3), dtype=np.uint8)
    cv2.putText(img, "INITIALIZING CAMERA...", (100, H // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()

frame_buffer = _create_standby_frame()
frame_lock = threading.Lock()
state_lock = threading.Lock()

state = {
    "fire_detected": False,
    "fire_conf": 0.0,
    "fire_box": None,
    "socket_detected": False,
    "socket_conf": 0.0,
    "socket_box": None,
    "pixel_distance": None,
    "cm_distance": None,
    "decision": "NO FIRE",
    "fps": 0.0
}

def cleanup():
    global arduino_serial
    try:
        if arduino_serial and arduino_serial.is_open:
            arduino_serial.write(b"STOP_ALL\n")
            arduino_serial.close()
            print("ðŸ›‘ [ARDUINO USB] Stopped and closed.")
    except:
        pass
    try:
        url = f"http://{RASPBERRY_IP}:{RASPBERRY_PORT}/command/STOP_ALL"
        requests.get(url, timeout=0.3)
    except:
        pass
    if camera is not None and camera.isOpened():
        camera.release()

atexit.register(cleanup)

def pixel_to_cm(px):
    return round(px * PIXEL_TO_CM, 2)

def safety_zone(box):
    x1, y1, x2, y2 = box
    return (
        x1 - SAFETY_MARGIN,
        y1 - SAFETY_MARGIN,
        x2 + SAFETY_MARGIN,
        y2 + SAFETY_MARGIN
    )

def box_distance(f, s):
    fx1, fy1, fx2, fy2 = f
    sx1, sy1, sx2, sy2 = s
    dx = max(sx1 - fx2, 0, fx1 - sx2)
    dy = max(sy1 - fy2, 0, fy1 - sy2)
    return float(np.sqrt(dx * dx + dy * dy))

def get_best(boxes):
    if boxes is None or len(boxes) == 0:
        return None, 0.0
    best = max(boxes, key=lambda b: float(b.conf[0]))
    x1, y1, x2, y2 = map(int, best.xyxy[0])
    return (x1, y1, x2, y2), float(best.conf[0])

def draw(frame, box, color, label, conf):
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(frame, f"{label} {conf:.2f}", (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

def process_frame(frame, fps):
    fire_res = fire_model.predict(frame, conf=CONF_FIRE, imgsz=IMGSZ, verbose=False)[0]
    socket_res = socket_model.predict(frame, conf=CONF_SOCKET, imgsz=IMGSZ, verbose=False)[0]

    fire_box, fire_conf = get_best(fire_res.boxes)
    socket_box, socket_conf = get_best(socket_res.boxes)

    fire_detected = fire_box is not None
    socket_detected = socket_box is not None

    pixel_distance = None
    cm_distance = None
    decision = "NO FIRE"

    if fire_box:
        draw(frame, fire_box, (0, 0, 255), "FIRE", fire_conf)

    if socket_box:
        draw(frame, socket_box, (255, 0, 0), "SOCKET", socket_conf)

    if fire_box and socket_box:
        zone = safety_zone(socket_box)
        pixel_distance = box_distance(fire_box, zone)
        cm_distance = pixel_to_cm(pixel_distance)
        decision = "FOAM PUMP" if pixel_distance <= THRESHOLD else "WATER PUMP"
    elif fire_box:
        decision = "WATER PUMP"

    # ZONE INTEGRATION POINT: replace distance-based decision with zone_engine.resolve_tactical_decision()
    # Expected signature: decision = zone_engine.resolve_tactical_decision(fire_box, zones)
    send_arduino_command(decision)

    cv2.putText(frame, f"Decision : {decision}", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    if pixel_distance is not None:
        cv2.putText(frame, f"Pixel : {pixel_distance:.1f}", (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"CM : {cm_distance:.2f}", (15, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"FPS : {fps:.1f}", (15, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    return frame, {
        "fire_detected": fire_detected,
        "fire_conf": round(fire_conf, 2),
        "fire_box": fire_box,
        "socket_detected": socket_detected,
        "socket_conf": round(socket_conf, 2),
        "socket_box": socket_box,
        "pixel_distance": pixel_distance,
        "cm_distance": cm_distance,
        "decision": decision,
        "fps": round(fps, 1)
    }

def _camera_loop():
    """Background thread: captures frames, runs inference, updates shared buffer."""
    global frame_buffer, camera
    last = time.perf_counter()
    while True:
        ok, frame = camera.read()
        if not ok:
            time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (W, H))

        now = time.perf_counter()
        fps = 1 / max(now - last, 1e-6)
        last = now

        try:
            frame, data = process_frame(frame, fps)
            with state_lock:
                state.update(data)
        except Exception as e:
            print(f"[WARN] process_frame error: {e}")

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok:
            with frame_lock:
                frame_buffer = buf.tobytes()

        time.sleep(0.01)


threading.Thread(target=_camera_loop, daemon=True).start()


def generate_frames():
    """Flask streaming: yields latest JPEG frame from shared buffer."""
    while True:
        with frame_lock:
            buf = frame_buffer
        if buf is None:
            time.sleep(0.05)
            continue
        yield (b'--frame\r\n'
               b'Content-Type:image/jpeg\r\n\r\n' +
               buf + b'\r\n')
        time.sleep(0.03)

@app.route("/")
def index():
    return render_template("Doma_flame_fighter_UI.html")

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/detection")
def api_detection():
    with state_lock:
        return jsonify(dict(state))

@app.route("/health")
def health():
    return jsonify({
        "status": "OK",
        "camera": camera.isOpened(),
        "camera_index": selected_cam_index,
        "camera_label": selected_cam_label,
        "arduino_usb": arduino_serial is not None and arduino_serial.is_open,
        "fire_model": FIRE_MODEL.name,
        "socket_model": SOCKET_MODEL.name
    })

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    ip = get_local_ip()
    print("=" * 55)
    print("Flame Fighter System (Laptop Server Running Auto-Control)")
    print("=" * 55)
    print(f"Dashboard : http://{ip}:{PORT}")
    print("=" * 55)

    try:
        app.run(
            host="0.0.0.0",
            port=PORT,
            threaded=True,
            debug=False,
            use_reloader=False
        )
    finally:
        cleanup()