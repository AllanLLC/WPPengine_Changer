import subprocess
import time
import threading
import psutil
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'persona-wallpaper-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

APP_WALLPAPERS = {
    "P3R.exe": {
        "path": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\3030059203\project.json",
        "game": "p3r",
        "name": "Persona 3 Reload",
    },
    "P4G.exe": {
        "path": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\1642100196\project.json",
        "game": "p4g",
        "name": "Persona 4 Golden",
    },
    "P5R.exe": {
        "path": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\2062717574\project.json",
        "game": "p5r",
        "name": "Persona 5 Royal",
    },
}

WALLPAPER_ENGINE = r"C:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine/wallpaper32.exe"

state = {
    "running": False,
    "active_game": None,
    "active_exe": None,
    "log": [],
}

monitor_thread = None


def add_log(msg, level="info"):
    entry = {"time": time.strftime("%H:%M:%S"), "msg": msg, "level": level}
    state["log"].insert(0, entry)
    if len(state["log"]) > 50:
        state["log"].pop()
    socketio.emit("log", entry)


def is_running(app_name):
    for proc in psutil.process_iter(['name']):
        try:
            if app_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def find_active_game():
    for exe in APP_WALLPAPERS:
        if is_running(exe):
            return exe
    return None


def change_wallpaper(path):
    try:
        subprocess.Popen([WALLPAPER_ENGINE, "-control", "openWallpaper", "-file", path, "-monitor", "1"])
        return True
    except Exception as e:
        add_log(f"Erro ao trocar wallpaper: {e}", "error")
        return False


def monitor_loop():
    last_game = None
    add_log("Monitoramento iniciado", "success")

    while state["running"]:
        exe = find_active_game()

        if exe and exe != last_game:
            info = APP_WALLPAPERS[exe]
            state["active_game"] = info["game"]
            state["active_exe"] = exe
            last_game = exe
            change_wallpaper(info["path"])
            add_log(f"{info['name']} detectado — wallpaper aplicado", "success")
            socketio.emit("game_change", {"game": info["game"], "name": info["name"], "exe": exe})

        elif not exe and last_game:
            last_game = None
            state["active_game"] = None
            state["active_exe"] = None
            name = APP_WALLPAPERS.get(last_game, {}).get("name", last_game) if last_game else "jogo"
            add_log("Nenhum jogo em execução", "info")
            socketio.emit("game_change", {"game": None, "name": None, "exe": None})

        time.sleep(10)

    add_log("Monitoramento pausado", "warning")
    socketio.emit("game_change", {"game": state["active_game"], "name": None, "exe": None})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/state')
def get_state():
    return jsonify(state)


@app.route('/api/start', methods=['POST'])
def start():
    global monitor_thread
    if not state["running"]:
        state["running"] = True
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        socketio.emit("status_change", {"running": True})
    return jsonify({"ok": True})


@app.route('/api/stop', methods=['POST'])
def stop():
    state["running"] = False
    state["active_game"] = None
    state["active_exe"] = None
    socketio.emit("status_change", {"running": False})
    socketio.emit("game_change", {"game": None, "name": None, "exe": None})
    return jsonify({"ok": True})


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)
