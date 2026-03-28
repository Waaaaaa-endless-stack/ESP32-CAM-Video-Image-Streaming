import camera
import network
import socket
import time

# WiFi 配置（改成你的路由器）
WIFI_SSID = ""
WIFI_PASSWORD = ""

# PC 端地址（运行 web.py 的机器）
VIDEO_ADDR = ("", 10086)
CMD_PORT = 10087


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        time.sleep_ms(100)
    print("wifi 已连接")
    print("ConnectState:", wlan.isconnected())
    print("network config:", wlan.ifconfig())
    return wlan


def init_camera():
    # 初始化摄像头并应用默认参数
    camera.init(0, format=camera.JPEG)
    camera.flip(0)
    camera.mirror(1)
    camera.framesize(camera.FRAME_SVGA)
    camera.speffect(camera.EFFECT_NONE)
    camera.whitebalance(camera.WB_HOME)
    camera.saturation(0)
    camera.brightness(0)
    camera.contrast(0)
    camera.quality(20)


def reinit_camera():
    try:
        camera.deinit()
    except Exception:
        pass
    time.sleep_ms(200)
    init_camera()
    time.sleep_ms(100)


def set_framesize(name):
    table = {
        "QVGA": camera.FRAME_QVGA,
        "VGA": camera.FRAME_VGA,
        "SVGA": camera.FRAME_SVGA,
        "XGA": camera.FRAME_XGA,
        "SXGA": camera.FRAME_SXGA,
        "UXGA": camera.FRAME_UXGA,
    }
    if name in table:
        camera.framesize(table[name])
        return True
    return False


def apply_command(cmd):
    # 命令格式：k=v;k=v，例如 framesize=VGA;quality=18
    if not cmd:
        return

    if cmd == "reinit=1":
        print("收到重初始化命令")
        reinit_camera()
        return

    for item in cmd.split(";"):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        try:
            if k == "framesize":
                print("set framesize:", v, set_framesize(v.upper()))
            elif k == "quality":
                camera.quality(int(v))
                print("set quality:", v)
            elif k == "brightness":
                camera.brightness(int(v))
                print("set brightness:", v)
            elif k == "contrast":
                camera.contrast(int(v))
                print("set contrast:", v)
            elif k == "saturation":
                camera.saturation(int(v))
                print("set saturation:", v)
            elif k == "mirror":
                camera.mirror(int(v))
                print("set mirror:", v)
            elif k == "flip":
                camera.flip(int(v))
                print("set flip:", v)
        except Exception as e:
            print("参数设置失败:", k, v, e)


def main():
    connect_wifi()
    init_camera()

    print("发送UDP包...")
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    cmd_sock.bind(("0.0.0.0", CMD_PORT))
    cmd_sock.settimeout(0.001)

    while True:
        # 非阻塞读取 Web 下发命令
        try:
            cmd_data, _ = cmd_sock.recvfrom(512)
            if cmd_data:
                apply_command(cmd_data.decode("utf-8").strip())
        except Exception:
            pass

        # 抓拍并发送到 PC；失败则自恢复
        try:
            buf = camera.capture()
            if not buf:
                raise OSError("capture empty")
            send_sock.sendto(buf, VIDEO_ADDR)
        except Exception as e:
            print("发送异常，重初始化:", e)
            reinit_camera()
            time.sleep_ms(100)


if __name__ == "__main__":
    main()
