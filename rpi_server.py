"""
Flame Fighter — Raspberry Pi Serial Bridge Server
================================================
يشتغل على الـ Raspberry Pi.
يستقبل HTTP commands من اللاب ويرسلها للـ Arduino عبر Serial (USB/UART).

تشغيل:
    pip install flask pyserial
    python rpi_server.py

Routes:
    GET  /command/<cmd>   — WATER_ON | FOAM_ON | STOP_ALL
    GET  /health          — حالة الاتصال
"""

from flask import Flask, jsonify
import serial
import serial.tools.list_ports
import time

app = Flask(__name__)

# ===================== CONFIG =====================
BAUD_RATE = 9600
PORT = 5001
# ==================================================

VALID_COMMANDS = {"WATER_ON", "FOAM_ON", "POWDER_ON", "GAS_ON", "STOP_ALL"}

arduino: serial.Serial | None = None


def find_arduino_port() -> str | None:
    """يبحث تلقائياً عن Arduino في الـ serial ports المتاحة."""
    candidates = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]
    ports = [p.device for p in serial.tools.list_ports.comports()]

    # Try known candidates first
    for c in candidates:
        if c in ports:
            return c

    # Fall back to first available port
    if ports:
        return ports[0]

    return None


def connect_serial():
    global arduino
    port = find_arduino_port()

    if not port:
        print("❌ No serial port found. Arduino not connected?")
        arduino = None
        return

    try:
        arduino = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # انتظر الـ Arduino يـ reset بعد فتح الـ Serial
        print(f"✅ Arduino connected on {port} @ {BAUD_RATE} baud")
    except Exception as e:
        print(f"❌ Serial connection failed on {port}: {e}")
        arduino = None


connect_serial()


def send_serial(cmd: str) -> bool:
    """يرسل الأمر للـ Arduino. يحاول إعادة الاتصال مرة واحدة لو انقطع."""
    global arduino
    if arduino is None or not arduino.is_open:
        print("⚠️ Arduino disconnected, retrying...")
        connect_serial()

    if arduino and arduino.is_open:
        try:
            arduino.write(f"{cmd}\n".encode())
            print(f"⚡ Serial → Arduino: {cmd}")
            return True
        except Exception as e:
            print(f"❌ Serial write error: {e}")
            arduino = None

    return False


@app.route("/command/<cmd>")
def command(cmd: str):
    if cmd not in VALID_COMMANDS:
        return jsonify({"error": f"Invalid command '{cmd}'"}), 400

    success = send_serial(cmd)

    if success:
        return jsonify({"status": "OK", "command": cmd})
    else:
        return jsonify({"error": "Arduino not connected or write failed"}), 503


@app.route("/health")
def health():
    port_name = arduino.port if arduino and arduino.is_open else None
    return jsonify({
        "status": "OK",
        "arduino_connected": arduino is not None and arduino.is_open,
        "port": port_name,
        "baud": BAUD_RATE
    })


if __name__ == "__main__":
    print("=" * 50)
    print("Flame Fighter — Raspberry Pi Bridge Server")
    print(f"Listening on port {PORT}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=PORT, debug=False)
