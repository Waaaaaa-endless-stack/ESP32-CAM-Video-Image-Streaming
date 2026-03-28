import socket
import time

import cv2
import numpy as np


# =========================
# PC 端实时图传接收参数
# =========================
# UDP 监听地址；ESP32-CAM 往这个端口发送 JPEG 数据
ADDR = ("", 10086)
# UDP 单包最大接收长度（64KB 上限）
BUFFER_SIZE = 65536
# OpenCV 预览窗口标题
WINDOW_NAME = "ESP32-CAM Real-time"

# =========================
# 可选录像参数
# =========================
# 是否同时保存为视频（实时图传本身不依赖落盘）
ENABLE_RECORD = True
# 输出文件名
RECORD_FILE = "esp32_cam_realtime.mp4"
# 写入视频时使用的目标帧率
RECORD_FPS = 20


def main() -> None:
    # 创建 UDP socket 并开始监听
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.bind(ADDR)
    print(f"等待数据... UDP {ADDR[0]}:{ADDR[1]}")

    # FPS 统计变量（每 1 秒更新一次）
    last_stat_time = time.time()
    stat_frames = 0
    fps = 0.0

    # 延迟创建视频写入器：只有在启用录像且拿到首帧后才创建
    writer = None

    try:
        # 主循环：持续接收 -> 解码 -> 显示 -> 可选录像
        while True:
            # 从 UDP 收到一帧 JPEG 二进制数据
            data, _ = sock.recvfrom(BUFFER_SIZE)
            if not data:
                continue

            # 直接把 JPEG 字节解码为图像，避免“先存盘再读取”的额外延迟
            np_buffer = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
            if frame is None:
                # 数据损坏或不完整时丢弃该帧，继续接收下一帧
                continue

            # 实时统计并刷新 FPS
            stat_frames += 1
            now = time.time()
            elapsed = now - last_stat_time
            if elapsed >= 1.0:
                fps = stat_frames / elapsed
                stat_frames = 0
                last_stat_time = now

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            # 实时预览窗口
            cv2.imshow(WINDOW_NAME, frame)

            if ENABLE_RECORD:
                if writer is None:
                    # 录像尺寸必须与首帧一致，所以这里基于首帧初始化
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(RECORD_FILE, fourcc, RECORD_FPS, (w, h))
                writer.write(frame)

            # 按 q 退出
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        # 统一资源清理，防止文件句柄/窗口泄露
        if writer is not None:
            writer.release()
        sock.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
