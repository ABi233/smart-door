import wiringpi
from wiringpi import GPIO
import time
from flask import Flask, jsonify
import threading

app = Flask(__name__)

PORT_NUMBER = 2 # 使用zero3上wPi为2的GPIO串口
door_open = False # 全局变量，用于存储门的当前状态, 访问需要获得线程锁
door_lock = threading.Lock() # 创建一个锁

# 控制GPIO的函数, 调用一次则开门，中间有5秒冷却期
def switch():
    global door_open
    wiringpi.digitalWrite(PORT_NUMBER, GPIO.HIGH)
    time.sleep(5)  # 开关打开3秒之后，自动关上。
    wiringpi.digitalWrite(PORT_NUMBER, GPIO.LOW)
    with door_lock:  # 使用锁来同步对 door_open 的访问
        door_open = False  # 重置门的状态

@app.route('/Open', methods=['GET'])
def open():
    global door_open
    with door_lock:  # 使用锁来同步对 door_open 的访问
        if not door_open:  # 如果门未开，则执行switch函数
            door_open = True  # 设置门的状态为开
            threading.Thread(target=switch).start()  # 在新线程中运行 switch 函数
            return jsonify({"status_code": 0, "message": "Door is opening"})
        else:
            return jsonify({"status_code": 1, "message": "Door is already open"})

if __name__ == '__main__':
    wiringpi.wiringPiSetup()
    wiringpi.pinMode(PORT_NUMBER, GPIO.OUTPUT)
    wiringpi.digitalWrite(PORT_NUMBER, GPIO.LOW)
    app.run(host='192.168.2.116', port=8080, threaded=True)
