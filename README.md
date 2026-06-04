# SmartDoor

智能门禁服务使用python库实现对GPIO口的控制，从而实现对门禁继电器开关的控制。

## jetson

英伟达提供用于jetson的[GPIO](https://github.com/NVIDIA/jetson-gpio)

jetson-gpio控制口的使用参考[这篇笔记](https://rw4pssarx37.feishu.cn/wiki/L5u9ws22QiWTLUkGcAbcWIEqnMf?from=from_copylink)

## orangepi-zero3

[GPIO测试](http://www.orangepi.cn/orangepiwiki/index.php/Orange_Pi_Zero_3#26pin_GPIO.E5.8F.A3.E6.B5.8B.E8.AF.95)

[wiringOP-Python的安装使用方法](http://www.orangepi.cn/orangepiwiki/index.php/Orange_Pi_Zero_3#wiringOP-Python.E7.9A.84.E5.AE.89.E8.A3.85.E4.BD.BF.E7.94.A8.E6.96.B9.E6.B3.95)

zero3 gpio使用参考[这篇笔记](https://rw4pssarx37.feishu.cn/wiki/L5u9ws22QiWTLUkGcAbcWIEqnMf?from=from_copylink)

# Api Endpoint

## 打开门禁

- **URL:** `/Open`
- **Method:** `GET`
- **Description:** 调用次API开门，每次调用API都有5秒冷却时间，在此期间再调用api将返回Error回复。
- **Responses:**
  - **Success:** 
    - **Code:** 200 
    - **Content:** `{"status_code": 0, "message": "Door is opening"}`
  - **Error (Door already open):** 
    - **Code:** 200 
    - **Content:** `{"status_code": 1, "message": "Door is already open"}`

# 服务运行流程

## 初始化

- GPIO库被配置为控制一个特定的端口`PORT_NUMBER`，该端口与物理门锁相连。
- `door_open`变量用于跟踪门的状态（开或关）。
- `door_lock`是一个线程锁，用于在修改`door_open`变量时保证线程安全。

## 处理开门请求

当接收到对`/Open`端点的GET请求时，会执行`open`函数：

1. **获取锁**：通过`with door_lock`获取锁，确保在检查或修改`door_open`变量时，不会有其他线程同时进行修改。
   
2. **检查门的状态**：如果`door_open`为`False`（门是关的），则继续执行；如果为`True`（门已开），则返回一个消息表示门已经是开着的，不需要再次打开。

3. **开门**：如果门是关的，将`door_open`设置为`True`，表明门即将开启。然后，创建并启动一个新的线程，该线程执行`switch`函数来控制GPIO，实际上执行开门操作。

## 执行开门操作

`switch`函数在一个新的线程中执行，以不阻塞主Web服务线程：

1. **控制GPIO**：首先，通过GPIO库将门锁的GPIO端口设置为`LOW`，触发开门动作。
   
2. **等待**：执行`time.sleep(5)`，模拟门开启后的冷却时间，期间不接受新的开门请求。

3. **关闭门**：冷却时间结束后，将GPIO端口设置回`HIGH`，模拟关闭门的动作。

4. **重置门状态**：使用`with door_lock`获取锁，然后将`door_open`重置为`False`，表示门现在是关闭的，新的开门请求可以被接受了。

## 线程安全

- **线程锁（`door_lock`）**：在修改全局变量`door_open`或在检查它的值时使用，以防止并发访问造成的竞态条件。锁确保了在任何时候，只有一个线程可以修改门的状态。

- **线程使用**：开门操作（`switch`函数）在一个独立的线程中执行，这允许Flask应用继续响应其他HTTP请求，包括对`/Open`端点的新请求。这意味着Web服务不会因为等待开门操作的完成而变得无响应。

- 这个服务使用flask编写，由于flask服务器本身不支持多线程操作，但是开锁这个行为有5秒冷却期，如果直接在服务主线程中执行这个冷却操作，则会阻塞服务运行。所以引入线程和线程.

# 配置开发环境 

## 创建虚拟环境

```bash
python3 -m venv venv
```

## 激活虚拟环境

  ```bash
  source venv/bin/activate
  ```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 离开虚拟环境

```bash
deactivate
```

# 启动服务
配置systemd的单元文件，现在的文件存放在`/etc/systemd/system/`中，配置如下, 其中`ExecStart`字段按照实际的路径进行测试:

```
[Unit]
Description=Smart Door Service
After=syslog.target network.target remote-fs.target nss-lookup.target network-online.target
Requires=network-online.target

[Service]
User=root
Group=root
WorkingDirectory=/root
Environment="PATH=/home/xubai/SmartDoor/venv/bin"
ExecStart=python3 /path/to/sample_xx.py
Restart=always
RestartSec=5
StartLimitInterval=30
StartLimitBurst=50

[Install]
WantedBy=multi-user.target
```

- `systemctl start smartdoor.service`启动服务
  - `systemctl enable smartdoor.service`服务设置开机自启
- `systemctl status smartdoor.service`查看服务运行状态
- 现在配置了自动重启 