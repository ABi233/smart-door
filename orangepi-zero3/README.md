# Orangepi配置环境 

## Wi-Fi 自动检查与恢复

[wifi-watchdog 部署与维护说明](./wifi-watchdog/README.md)

每分钟检查无线连接及局域网网关，异常时尝试重连，连续 10 次失败后重启系统。
支持开机自启，异常日志持久化保存并自动轮转。

## 安装适配orangepi的wiringpi

[wiringOP-Python的安装使用方法](http://www.orangepi.cn/orangepiwiki/index.php/Orange_Pi_Zero_3#wiringOP-Python.E7.9A.84.E5.AE.89.E8.A3.85.E4.BD.BF.E7.94.A8.E6.96.B9.E6.B3.95)

以下操作需要在root账户下

```bash
apt update

apt -y install git swig python3-dev python3-setuptools

cd /usr/src/wiringOP-Python

python3 generate-bindings.py > bindings.i

python3 setup.py install
```

## 安装flask

因为orangepi被配置了PEP 668：Externally Managed Environment（外部管理环境） 限制, 所以需要使用系统包管理器(apt)来安装

```bash
sudo apt update

sudo apt install python3-flask -y
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
