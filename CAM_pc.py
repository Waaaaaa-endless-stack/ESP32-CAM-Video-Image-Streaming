import network
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
wlan.active(True)
a = wlan.scan()
print(a)
wlan.connect("你的WIFI名称", "你的WIFI密码")      
# cam 的WIFI模块不支持5G
while not wlan.isconnected():
    pass

print('wifi 已连接')
print('ConnectState:',wlan.isconnected())
print('network config:',wlan.ifconfig())


import camera

#ESP32-CAM（默认配置）-https://bit.ly/2Ndn8tN
camera.init(0, format=camera.JPEG)
 
#其他设置：
#上翻下翻899999
camera.flip(0)
#左/右
camera.mirror(1)
 
# 分辨率
camera.framesize(camera.FRAME_SVGA)
# 选项如下：
# FRAME_96X96 FRAME_QQVGA FRAME_QCIF FRAME_HQVGA FRAME_240X240
# FRAME_QVGA FRAME_CIF FRAME_HVGA FRAME_VGA FRAME_SVGA
# FRAME_XGA FRAME_HD FRAME_SXGA FRAME_UXGA FRAME_FHD
# FRAME_P_HD FRAME_P_3MP FRAME_QXGA FRAME_QHD FRAME_WQXGA
# FRAME_P_FHD FRAME_QSXGA
# 有关详细信息，请查看此链接：https://bit.ly/2YOzizz
 
#特效
camera.speffect(camera.EFFECT_NONE)
#选项如下：
# 效果\无（默认）效果\负效果\ BW效果\红色效果\绿色效果\蓝色效果\复古效果
# EFFECT_NONE (default) EFFECT_NEG \EFFECT_BW\ EFFECT_RED\ EFFECT_GREEN\ EFFECT_BLUE\ EFFECT_RETRO
 
#白平衡
camera.whitebalance(camera.WB_HOME)
#选项如下：
# WB_NONE (default) WB_SUNNY WB_CLOUDY WB_OFFICE WB_HOME
 
#饱和
camera.saturation(0)
#-2,2（默认为0）. -2灰度
# -2,2 (default 0). -2 grayscale 
 
#亮度
camera.brightness(0)
#-2,2（默认为0）. 2亮度
# -2,2 (default 0). 2 brightness
 
#对比度
camera.contrast(0)
#-2,2（默认为0）.2高对比度
#-2,2 (default 0). 2 highcontrast
 
#质量
camera.quality(20)
#10-63数字越小质量越高
 
#拍照,buf为jpg二进制数据,可以直接存储为jpg
buf = camera.capture()



# 客户端(esp32 cam)
import socket
 
#服务端地址和端口,127.0.0.1改成你的服务端地址
ADDR = ('127.0.0.1',10086)
 
print ("发送UDP包...")
#socket连接
sendSock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,0)
#拍照发送
while True:
    buf = camera.capture()
    #发送数据
    sendSock.sendto(buf,ADDR)
    print ("发送完毕...")

#关闭socket连接
sendSock.close()
