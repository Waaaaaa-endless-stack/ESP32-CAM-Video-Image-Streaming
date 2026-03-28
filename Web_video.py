import json
import hashlib
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


# 视频接收端口（ESP32-CAM 发送 JPEG 到这里）
VIDEO_UDP_ADDR = ("", 10086)
VIDEO_BUFFER_SIZE = 65536

# 控制命令端口（PC -> ESP32-CAM）
CAM_CMD_PORT = 10087

# Web 服务监听地址
WEB_ADDR = ("0.0.0.0", 8081)


# =========================
# 简单登录口令（cookie 会话）
# =========================
# 为了简单易用：只做“同网段简单防误操作”。
# 生产环境建议改成 HTTPS + 用户体系或更严格鉴权。
LOGIN_PASSWORD = "123456"
AUTH_COOKIE_NAME = "esp32cam_auth"
AUTH_TOKEN = hashlib.sha256(LOGIN_PASSWORD.encode("utf-8")).hexdigest()

LATEST_JPEG = None
LATEST_SOURCE_IP = None
LATEST_FRAME_AT = 0.0
# 最近一段时间的到帧时间戳，用于估算接收帧率和延迟稳定性
FRAME_TIMES = deque(maxlen=120)
LOCK = threading.Lock()

# 最近一次成功下发到摄像头的参数（供网页回显）
CFG_LOCK = threading.Lock()
LAST_CONFIG = {}
LAST_CONFIG_AT = 0.0

LOGIN_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ESP32-CAM 登录</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 16px; background: #f7f7f7; }
    .card { background: #fff; border-radius: 8px; padding: 16px; max-width: 420px; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
    input, button { padding: 10px; font-size: 14px; width: 100%; box-sizing: border-box; margin-top: 8px; }
    button { cursor: pointer; }
    #msg { margin-top: 10px; color: #b00; }
  </style>
</head>
<body>
  <h2>ESP32-CAM 控制台登录</h2>
  <div class="card">
    <form id="loginForm">
      <label>登录口令</label>
      <input name="password" type="password" placeholder="输入口令" required />
      <button type="submit">登录</button>
    </form>
    <div id="msg"></div>
  </div>
<script>
const msgEl = document.getElementById("msg");
document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = new URLSearchParams(fd).toString();
  try {
    const r = await fetch("/api/login", {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body
    });
    const j = await r.json();
    if (!j.ok) throw new Error(j.message || "登录失败");
    window.location.href = "/";
  } catch (e2) {
    msgEl.textContent = e2.message || "登录失败";
  }
});
</script>
</body>
</html>
"""

HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ESP32-CAM Web 控制台</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 16px; background: #f7f7f7; }
    .row { display: flex; gap: 16px; flex-wrap: wrap; }
    .card { background: #fff; border-radius: 8px; padding: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
    img { max-width: 100%; height: auto; background: #000; border-radius: 6px; }
    label { display: block; margin: 8px 0 4px; font-weight: 600; }
    input, select, button { padding: 8px; font-size: 14px; width: 100%; box-sizing: border-box; }
    button { margin-top: 10px; cursor: pointer; }
    #status { margin-top: 8px; color: #333; min-height: 1.4em; }
    #status.alert { color: #b00; font-weight: 700; }
    #currentConfig { margin-top: 10px; font-size: 13px; color: #333; white-space: pre-wrap; word-break: break-word; }
    .presetBox { margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; }
  </style>
</head>
<body>
  <h2>ESP32-CAM 实时图传 + 参数设置</h2>
  <div class="row">
    <div class="card" style="flex: 2; min-width: 360px;">
      <img src="/stream.mjpg" alt="实时画面" />
      <div id="status">等待状态...</div>
      <div id="currentConfig">当前参数：-</div>
    </div>
    <div class="card" style="flex: 1; min-width: 260px;">
      <div class="presetBox">
        <label>保存预设名称</label>
        <input id="presetName" placeholder="例如：室内SVGA" />
        <button id="savePresetBtn" type="button">保存预设</button>

        <label>加载预设</label>
        <select id="presetSelect"></select>
        <button id="loadPresetBtn" type="button">加载到表单</button>
      </div>

      <form id="cfgForm">
        <label>分辨率</label>
        <select name="framesize">
          <option value="QVGA">QVGA</option>
          <option value="VGA">VGA</option>
          <option value="SVGA" selected>SVGA</option>
          <option value="XGA">XGA</option>
          <option value="SXGA">SXGA</option>
          <option value="UXGA">UXGA</option>
        </select>
        <label>质量(10-63，越小越清晰)</label>
        <input name="quality" type="number" min="10" max="63" value="20" />
        <label>亮度(-2~2)</label>
        <input name="brightness" type="number" min="-2" max="2" value="0" />
        <label>对比度(-2~2)</label>
        <input name="contrast" type="number" min="-2" max="2" value="0" />
        <label>饱和度(-2~2)</label>
        <input name="saturation" type="number" min="-2" max="2" value="0" />
        <label>镜像(0/1)</label>
        <input name="mirror" type="number" min="0" max="1" value="1" />
        <label>翻转(0/1)</label>
        <input name="flip" type="number" min="0" max="1" value="0" />
        <button type="submit">应用到摄像头</button>
      </form>
      <button id="reinitBtn">摄像头重初始化</button>
    </div>
  </div>
<script>
const statusEl = document.getElementById("status");
const currentConfigEl = document.getElementById("currentConfig");
const presetNameEl = document.getElementById("presetName");
const presetSelectEl = document.getElementById("presetSelect");
const PRES_KEY = "esp32cam_presets_v1";

function getFormConfig() {
  const fd = new FormData(document.getElementById("cfgForm"));
  const obj = {};
  for (const [k, v] of fd.entries()) obj[k] = v;
  return obj;
}

function setFormConfig(cfg) {
  const form = document.getElementById("cfgForm");
  for (const [k, v] of Object.entries(cfg || {})) {
    const el = form.elements.namedItem(k);
    if (el) el.value = v;
  }
}

function loadPresets() {
  try {
    return JSON.parse(localStorage.getItem(PRES_KEY) || "{}");
  } catch (e) {
    return {};
  }
}

function savePresets(p) {
  localStorage.setItem(PRES_KEY, JSON.stringify(p || {}));
}

function refreshPresetSelect() {
  const presets = loadPresets();
  const names = Object.keys(presets);
  presetSelectEl.innerHTML = "";
  if (names.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "（暂无预设）";
    presetSelectEl.appendChild(opt);
    return;
  }
  for (const n of names) {
    const opt = document.createElement("option");
    opt.value = n;
    opt.textContent = n;
    presetSelectEl.appendChild(opt);
  }
}

refreshPresetSelect();

document.getElementById("savePresetBtn").addEventListener("click", () => {
  const name = (presetNameEl.value || "").trim();
  if (!name) return alert("请输入预设名称");
  const cfg = getFormConfig();
  const presets = loadPresets();
  presets[name] = cfg;
  savePresets(presets);
  refreshPresetSelect();
  alert("预设已保存：" + name);
});

document.getElementById("loadPresetBtn").addEventListener("click", () => {
  const name = presetSelectEl.value;
  const presets = loadPresets();
  if (!name || !presets[name]) return;
  setFormConfig(presets[name]);
});

function formatConfig(cfg) {
  if (!cfg || Object.keys(cfg).length === 0) return "-";
  const keys = ["framesize","quality","brightness","contrast","saturation","mirror","flip"];
  const lines = [];
  for (const k of keys) {
    if (cfg[k] !== undefined) lines.push(`${k}=${cfg[k]}`);
  }
  return lines.join("\\n");
}

async function pollStatus() {
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    const age = s.last_frame_age_ms;
    const src = s.source_ip || "-";
    const fps = (s.rx_fps || 0).toFixed(1);

    // 断流告警：例如 2 秒无帧（>2000ms）则红色提示
    if (age < 0 || age > 2000) {
      statusEl.classList.add("alert");
      statusEl.textContent = `断流/无画面 | 来源IP: ${src} | 延迟: ${age} ms | 接收FPS: ${fps}`;
    } else {
      statusEl.classList.remove("alert");
      statusEl.textContent = `来源IP: ${src} | 延迟: ${age} ms | 接收FPS: ${fps}`;
    }

    currentConfigEl.textContent = "当前参数：\n" + formatConfig(s.last_config);
  } catch (e) {
    statusEl.textContent = "状态获取失败";
  }
}
setInterval(pollStatus, 500);
pollStatus();

document.getElementById("cfgForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = new URLSearchParams(fd).toString();
  const r = await fetch("/api/config", {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body
  });
  const j = await r.json();
  alert(j.message || "ok");
});

document.getElementById("reinitBtn").addEventListener("click", async () => {
  const r = await fetch("/api/reinit", {method: "POST"});
  const j = await r.json();
  alert(j.message || "ok");
});
</script>
</body>
</html>
"""


def recv_video_loop() -> None:
    global LATEST_JPEG, LATEST_SOURCE_IP, LATEST_FRAME_AT

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.bind(VIDEO_UDP_ADDR)
    print("视频UDP监听:", VIDEO_UDP_ADDR)

    while True:
        data, addr = sock.recvfrom(VIDEO_BUFFER_SIZE)
        if not data:
            continue
        now = time.time()
        with LOCK:
            LATEST_JPEG = data
            LATEST_SOURCE_IP = addr[0]
            LATEST_FRAME_AT = now
            FRAME_TIMES.append(now)


def send_cam_cmd(command: str) -> tuple[bool, str]:
    with LOCK:
        cam_ip = LATEST_SOURCE_IP
    if not cam_ip:
        return False, "尚未收到视频流，无法确定 ESP32-CAM IP"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        sock.sendto(command.encode("utf-8"), (cam_ip, CAM_CMD_PORT))
        sock.close()
        return True, "命令已发送: " + command
    except Exception as e:
        return False, "命令发送失败: " + str(e)


class Handler(BaseHTTPRequestHandler):
    def _get_cookie(self, name: str):
        raw = self.headers.get("Cookie", "")
        if not raw:
            return None
        parts = raw.split(";")
        for p in parts:
            p = p.strip()
            if p.startswith(name + "="):
                return p.split("=", 1)[1]
        return None

    def _is_authed(self) -> bool:
        token = self._get_cookie(AUTH_COOKIE_NAME)
        return token == AUTH_TOKEN

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        u = urlparse(self.path)
        path = u.path
        query = u.query

        if path in ("/", "/index.html"):
            if not self._is_authed():
                body = LOGIN_PAGE.encode("utf-8")
            else:
                # 支持通过 URL query 一键下发参数（登录后才允许）
                # 例如 /?framesize=SVGA&quality=20&brightness=0...
                if query:
                    params = parse_qs(query, keep_blank_values=False)
                    allow_keys = {
                        "framesize",
                        "quality",
                        "brightness",
                        "contrast",
                        "saturation",
                        "mirror",
                        "flip",
                    }
                    command_parts = []
                    cfg = {}
                    for key, values in params.items():
                        if key in allow_keys and values:
                            command_parts.append(f"{key}={values[0]}")
                            cfg[key] = values[0]

                    if command_parts:
                        ok, _ = send_cam_cmd(";".join(command_parts))
                        if ok:
                            with CFG_LOCK:
                                LAST_CONFIG.clear()
                                LAST_CONFIG.update(cfg)
                                global LAST_CONFIG_AT
                                LAST_CONFIG_AT = time.time()

                    # 下发后重定向回主页，避免刷新重复下发
                    self.send_response(302)
                    self.send_header("Location", "/")
                    self.end_headers()
                    return

                body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path == "/api/status":
            if not self._is_authed():
                self._send_json(401, {"ok": False, "message": "未登录"})
                return
            with LOCK:
                src = LATEST_SOURCE_IP
                age_ms = int((time.time() - LATEST_FRAME_AT) * 1000) if LATEST_FRAME_AT else -1
                frame_times = list(FRAME_TIMES)

            rx_fps = 0.0
            if len(frame_times) >= 2:
                span = frame_times[-1] - frame_times[0]
                if span > 0:
                    rx_fps = (len(frame_times) - 1) / span
            with CFG_LOCK:
                cfg = dict(LAST_CONFIG)
                cfg_time = LAST_CONFIG_AT
            self._send_json(
                200,
                {
                    "source_ip": src,
                    "last_frame_age_ms": age_ms,
                    "rx_fps": round(rx_fps, 2),
                    "last_config": cfg,
                    "last_config_at": int(cfg_time * 1000),
                },
            )
            return

        if path == "/stream.mjpg":
            if not self._is_authed():
                self.send_response(401)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with LOCK:
                        frame = LATEST_JPEG
                    if frame:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(("Content-Length: %d\r\n\r\n" % len(frame)).encode("ascii"))
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.03)
            except (BrokenPipeError, ConnectionResetError):
                return
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        if self.path not in ("/api/login", "/api/config", "/api/reinit"):
            self.send_error(404, "Not Found")
            return

        if self.path == "/api/login":
            # 登录接口：POST 表单参数 password=xxxx
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="ignore")
            params = parse_qs(raw, keep_blank_values=False)
            pw = params.get("password", [""])[0]
            if pw == LOGIN_PASSWORD:
                # 设置 cookie 维持会话（简单实现：token 固定）
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", f"{AUTH_COOKIE_NAME}={AUTH_TOKEN}; Path=/; HttpOnly")
                body = json.dumps({"ok": True, "message": "登录成功"}, ensure_ascii=False).encode("utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._send_json(403, {"ok": False, "message": "口令错误"})
            return

        # 以下接口需要登录
        if not self._is_authed():
            self._send_json(401, {"ok": False, "message": "未登录"})
            return

        if self.path == "/api/reinit":
            ok, msg = send_cam_cmd("reinit=1")
            self._send_json(200 if ok else 400, {"ok": ok, "message": msg})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="ignore")
        params = parse_qs(raw, keep_blank_values=False)

        # 将表单转换成 "k=v;k=v" 格式，便于 ESP32 解析
        command_parts = []
        allow_keys = {"framesize", "quality", "brightness", "contrast", "saturation", "mirror", "flip"}
        cfg = {}
        for key, values in params.items():
            if key in allow_keys and values:
                command_parts.append(f"{key}={values[0]}")
                cfg[key] = values[0]

        if not command_parts:
            self._send_json(400, {"ok": False, "message": "没有有效参数"})
            return

        ok, msg = send_cam_cmd(";".join(command_parts))
        if ok:
            with CFG_LOCK:
                LAST_CONFIG.clear()
                LAST_CONFIG.update(cfg)
                LAST_CONFIG_AT = time.time()
        self._send_json(200 if ok else 400, {"ok": ok, "message": msg})

    def log_message(self, fmt: str, *args) -> None:
        # 精简 http 日志，避免刷屏
        return


def main() -> None:
    recv_thread = threading.Thread(target=recv_video_loop, daemon=True)
    recv_thread.start()

    httpd = ThreadingHTTPServer(WEB_ADDR, Handler)
    print("Web 服务启动: http://%s:%d" % (WEB_ADDR[0] or "127.0.0.1", WEB_ADDR[1]))
    httpd.serve_forever()


if __name__ == "__main__":
    main()
