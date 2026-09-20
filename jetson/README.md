# Jetson配置环境 

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
配置systemd的单元文件，`/etc/systemd/system/smartdoor.service`中，配置如下, 其中`ExecStart`字段按照实际的路径进行测试:

```
[Unit]
Description=Smart Door Service
After=syslog.target network.target remote-fs.target nss-lookup.target network-online.target
Requires=network-online.target

[Service]
User=root
Group=root
WorkingDirectory=/root
Environment="PATH=/path/to/venv/bin"
ExecStart=python3 /path/to/sample_xx.py
Restart=always
RestartSec=5
StartLimitInterval=30
StartLimitBurst=50

[Install]
WantedBy=multi-user.target
```

- `systemctl start smartdoor.service` 启动服务
  - `systemctl enable smartdoor.service` 服务设置开机自启
- `systemctl status smartdoor.service` 查看服务运行状态
