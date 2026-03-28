# Design-of-Video-Image-Transmission-System-Based-on-ESP32-CAM
MA
# ESP32-CAM 视频图像传输系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![MicroPython](https://img.shields.io/badge/MicroPython-v1.20+-red.svg)](https://micropython.org/)
[![ESP32](https://img.shields.io/badge/ESP32-ESP32--CAM-green.svg)](https://www.espressif.com/)

基于ESP32-CAM和MicroPython的实时视频图像传输系统，支持Web浏览器直接查看和PC端高级处理。

## ✨ 特性

- 📹 **实时视频流**：通过WiFi传输MJPEG视频流
- 🎯 **双模式支持**：
  - 独立Web服务器模式（ESP32-CAM直接输出）
  - UDP/TCP转发模式（PC端处理）
- 🔧 **可配置参数**：分辨率、画质、帧率动态调整

## 📋 系统架构

### 方案一：WIFI模块传输视频流
OV2640 --> ESP32-CAM  <--WiFi--> PC端CV2


### 方案二：PC服务器转发
ESP32-CAM --UDP/TCP--> PC Server --HTTP--> 浏览器


## 🚀 快速开始

### 硬件准备

| 硬件 | 数量 | 说明 |
|------|------|------|
| ESP32-CAM模块 | 1 | 带OV2640摄像头 |
| USB转TTL | 1 | 程序烧录 |
| 杜邦线 | 若干 | 连接用 |
| 5V/2A电源 | 1 | 必须保证供电充足 |

### 软件准备

- [Thonny IDE](https://thonny.org/) 或 [VS Code](https://code.visualstudio.com/)
- [esptool.py](https://github.com/espressif/esptool) - 固件烧录工具
- [MicroPython固件](https://github.com/lemariva/micropython-camera-driver) (带摄像头驱动)

### 安装步骤

#### 1. 烧录MicroPython固件

```bash
# 安装esptool
pip install esptool

# 擦除Flash
esptool.py --chip esp32 --port COM3 erase_flash

# 烧录固件

#### 2. 上传代码到ESP32-CAM
打开Thonny IDE

连接ESP32-CAM（工具 → 选项 → 解释器）

将 esp32_cam/ 目录下的文件上传到设备

修改 CAM_pc/web.py 中的WiFi配置

python(VS code/Cursor 配置python环境解释器均可)
# 修改为您的WiFi信息
SSID = "你的WiFi名称"
PASSWORD = "你的WiFi密码"

3. 运行程序
方案一：ESP32-CAM自动启动Web服务器

查看串口输出获取IP地址

浏览器访问 http://[ESP32_IP]

方案二：

bash
# 启动PC端服务器
cd pc_server
pip install -r requirements.txt
python udp_receiver.py


常见问题
Q: 摄像头初始化失败？
A:

检查供电（需5V/2A以上）

确认固件支持摄像头驱动

尝试硬件复位

Q: 画面花屏或有水纹？
A:

电源不足，更换高质量电源

检查摄像头排线是否接触良好

Q: UDP丢包严重？
A:

降低分辨率或帧率

确保ESP32和PC在同一局域网


📄 许可证
本项目采用MIT许可证 - 详见 LICENSE 文件

📧 联系方式
项目主页：[(https://github.com/Waaaaaa-endless-stack)]

问题反馈：[https://github.com/Waaaaaa-endless-stack/ESP32-CAM-Video-Image-Streaming/issues]

邮箱：zhengzha0.leo@outlook.com

🙏 致谢
MicroPython

lemariva/micropython-camera-driver

microdot

⭐ Star History
如果这个项目对您有帮助，请给个Star支持一






