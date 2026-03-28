#服务端
import socket,time
 
# 客户端ip及端口，为空则接收任意客户端发来的数据
ADDR = ('',10086)
recvSock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,0)
recvSock.bind(ADDR)
 
# 这里时间戳用来命名图片文件    
time_e = int(time.time())
# 当前时间戳的第N帧
zz = 0
#总帧数,此次为测试,可具体参考帧数来设置（我测试的效果大概为每秒6帧,录制20s,所以达到120张照片停止循环）
num = 0
print ("等待数据...")
 
while True:
    #接收的数据大小,建议比图片本身大,不然无法传输
    data = recvSock.recv(100000)
    #每次检查时间戳
    time_b = int(time.time())
    #每次循环帧数加1
    zz = zz + 1
    #如果时间戳+1秒,则帧数序号归零
    if time_b != time_e:
        time_e = time_b
        zz = 0
    #存储图片
    filename = str(time_e) + str(zz) + '.jpg'
    with open (filename,'wb') as f :
        f.write(data)
        f.close()
    print(filename)
    #总帧数
    num =  num + 1
    if num == 120:
        break
 
#将图片合成视频
import os
cv2 = __import__("cv2")
 
pic_path = '.'
pics_list = [i for i in os.listdir(pic_path) if i.endswith('.jpg')]
fps = 7  # 帧率,自行参考文件命名,我的大概是7
size = (800, 600)  # 视频尺寸,请根据图片实际尺寸设置,不然无法合成,SVGA为800*600
out_file_name = '{0}.mp4'.format('示例视频')  # 输出视频名称
out_path =  '.'  # 输出视频路径
out_file = os.path.join(out_path, out_file_name)
fourcc = cv2.VideoWriter_fourcc('D', 'I', 'V', 'X')
 
video = cv2.VideoWriter(out_file, fourcc, fps, size)
for item in pics_list:
    item = out_path + '/' + item
    img = cv2.imread(item)
    video.write(img)
video.release()
