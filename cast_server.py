"""
Веб-інтерфейс для трансляції відео/стріму на Chromecast.

Встановлення:
    pip install flask pychromecast

Запуск:
    python cast_server.py

Потім відкрий у браузері на цьому ж ПК:
    http://127.0.0.1:5000

На сторінці:
  - обери пристрій Chromecast зі списку (кнопка "Оновити список" — пошук у мережі)
  - встав пряме посилання на відео/стрім (.m3u8 для HLS, .mp4 теж підтримується)
  - "Транслювати" — почати відтворення на телевізорі
  - "Пауза" / "Продовжити" / "Стоп" — керування вже активною трансляцією
  - повзунок гучності — керує гучністю самого Chromecast-пристрою
"""

import threading
import pychromecast
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ---- Глобальний стан (спільний для всіх запитів) ----
lock = threading.Lock()
devices = {}           # name -> Chromecast object
browser = None
current_cast = None    # обраний Chromecast
current_mc = None      # його media_controller


def discover_devices():
    """Шукає Chromecast-пристрої у локальній мережі."""
    global devices, browser
    casts, br = pychromecast.get_chromecasts(timeout=10)
    with lock:
        devices = {c.name: c for c in casts}
        browser = br
    print(f"Знайдено пристроїв: {list(devices.keys())}")


PAGE = """
<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<title>Chromecast керування</title>
<style>
  body { font-family: sans-serif; background:#111; color:#eee; display:flex;
         flex-direction:column; align-items:center; padding-top:40px; }
  input, select, button { font-size:16px; padding:8px; margin:6px; border-radius:6px; border:none; }
  input[type=text] { width:420px; }
  button { background:#2a6df4; color:#fff; cursor:pointer; }
  button:hover { background:#1c54c9; }
  #status { margin-top:15px; color:#9f9; min-height:20px; text-align:center; }
  .row { display:flex; align-items:center; gap:10px; }
</style>
</head>
<body>
  <h2>Трансляція відео на Chromecast</h2>

  <div class="row">
    <select id="device"></select>
    <button onclick="refreshDevices()">Оновити список</button>
  </div>

  <input type="text" id="url" placeholder="Встав посилання на відео/стрім (.m3u8, .mp4...)">
  <button onclick="castVideo()">&#9654; Транслювати</button>

  <div class="row">
    <button onclick="control('pause')">&#9208; Пауза</button>
    <button onclick="control('resume')">&#9654; Продовжити</button>
    <button onclick="control('stop')">&#9632; Стоп</button>
  </div>

  <div class="row">
    <label>Гучність</label>
    <input type="range" id="volume" min="0" max="100" value="50" oninput="setVolume(this.value)">
  </div>

  <div id="status"></div>

<script>
function setStatus(t){ document.getElementById('status').innerText = t; }

async function refreshDevices(){
  setStatus('Пошук пристроїв...');
  const res = await fetch('/devices');
  const data = await res.json();
  const sel = document.getElementById('device');
  sel.innerHTML = '';
  data.devices.forEach(name => {
    const opt = document.createElement('option');
    opt.value = name; opt.innerText = name;
    sel.appendChild(opt);
  });
  setStatus(data.devices.length ? 'Знайдено: ' + data.devices.join(', ') : 'Пристроїв не знайдено');
}

async function castVideo(){
  const url = document.getElementById('url').value.trim();
  const device = document.getElementById('device').value;
  if(!url){ setStatus('Встав посилання на відео'); return; }
  setStatus('Трансляція...');
  const res = await fetch('/cast', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({url, device})
  });
  const data = await res.json();
  setStatus(data.message);
}

async function control(action){
  const res = await fetch('/' + action, {method:'POST'});
  const data = await res.json();
  setStatus(data.message);
}

async function setVolume(val){
  await fetch('/volume', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({level: val/100})
  });
}

window.onload = refreshDevices;
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/devices")
def list_devices():
    with lock:
        names = list(devices.keys())
    return jsonify({"devices": names})


@app.route("/cast", methods=["POST"])
def cast():
    global current_cast, current_mc
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    device_name = data.get("device")

    if not url:
        return jsonify({"message": "Порожнє посилання"}), 400

    with lock:
        if not devices:
            return jsonify({"message": "Пристроїв не знайдено. Натисни 'Оновити список'"}), 400
        cast_dev = devices.get(device_name) or next(iter(devices.values()))

    cast_dev.wait()
    mc = cast_dev.media_controller

    # Визначаємо content_type за розширенням посилання
    lower_url = url.lower()
    if lower_url.endswith(".m3u8"):
        content_type = "application/x-mpegurl"  # HLS
    elif lower_url.endswith(".mpd"):
        content_type = "application/dash+xml"   # MPEG-DASH
    else:
        content_type = "video/mp4"

    mc.play_media(url, content_type=content_type)
    mc.block_until_active(timeout=10)

    with lock:
        current_cast = cast_dev
        current_mc = mc

    return jsonify({"message": f"Транслюю на: {cast_dev.name}"})


@app.route("/pause", methods=["POST"])
def pause():
    with lock:
        mc = current_mc
    if not mc:
        return jsonify({"message": "Немає активної трансляції"}), 400
    mc.pause()
    return jsonify({"message": "Пауза"})


@app.route("/resume", methods=["POST"])
def resume():
    with lock:
        mc = current_mc
    if not mc:
        return jsonify({"message": "Немає активної трансляції"}), 400
    mc.play()
    return jsonify({"message": "Продовжено"})


@app.route("/stop", methods=["POST"])
def stop():
    with lock:
        mc = current_mc
    if not mc:
        return jsonify({"message": "Немає активної трансляції"}), 400
    mc.stop()
    return jsonify({"message": "Зупинено"})


@app.route("/volume", methods=["POST"])
def volume():
    with lock:
        cast_dev = current_cast
    data = request.get_json(force=True)
    level = float(data.get("level", 0.5))
    level = max(0.0, min(1.0, level))
    if not cast_dev:
        return jsonify({"message": "Немає обраного пристрою (спочатку почни трансляцію)"}), 400
    cast_dev.set_volume(level)
    return jsonify({"message": f"Гучність: {int(level * 100)}%"})


if __name__ == "__main__":
    threading.Thread(target=discover_devices, daemon=True).start()
    print("Сервер запущено: http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)