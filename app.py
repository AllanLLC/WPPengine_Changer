import subprocess
import time
import psutil

APP_WALLPAPERS = {
    "P3R.exe": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\3030059203\project.json",
    "P4G.exe": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\1642100196\project.json",
    "P5R.exe": r"C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\2062717574\project.json",
}

WALLPAPER_ENGINE = r"C:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine/wallpaper32.exe"

def ta_rodando(app_name):
    for proc in psutil.process_iter(['name']):
        try:
            if app_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def checar(lst):
    for app in lst:
        if ta_rodando(app):
            return app
    return None

def mudar_wallpaper(caminho):
    subprocess.run([WALLPAPER_ENGINE, "-control", "openWallpaper", "-file", caminho, "-monitor 1"])

if __name__ == "__main__":
    ultimo_game = None
    while True:
        game = checar(APP_WALLPAPERS)
        if game is not None and game != ultimo_game:
            mudar_wallpaper(APP_WALLPAPERS[game])
            ultimo_game = game
        elif game is None:
            ultimo_game = None
        time.sleep(10)