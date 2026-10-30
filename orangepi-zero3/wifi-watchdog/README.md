# Orange Pi Wi-Fi watchdog

每分钟检查 wlan0 的 NetworkManager 状态、IPv4 地址、默认网关及网关 ping。
异常后使用已有连接配置重连一次，连续 10 次失败后执行正常系统重启。
任何一次检查恢复正常即清零计数；开机前 120 秒不进行检查。

## 安装

需要板子运行 systemd，并使用 NetworkManager 管理 Wi-Fi。依赖 Python 3（仅标准库）、
`nmcli`、`ip` 和 `ping`；已在 Orange Pi Zero 3 的 Ubuntu 24.04 上验证。

从本地仓库根目录上传到板子：

```sh
scp -r orangepi-zero3/wifi-watchdog user@your-device:~/
ssh user@your-device
```

也可以直接在板子上的仓库中进入 `orangepi-zero3/wifi-watchdog` 目录安装。

安装前确认网卡和 Wi-Fi 连接 UUID：

```sh
nmcli device status
nmcli -f NAME,UUID,TYPE connection show
```

将 `user@your-device` 替换为实际 SSH 用户和设备地址。默认网卡为 `wlan0`，
安装前按实际情况修改 `wifi-watchdog.conf` 中的 `interface`，并将
`connection_uuid = YOUR_WIFI_CONNECTION_UUID` 替换为上面查询到的实际 Wi-Fi 连接 UUID。
网关从无线接口的默认路由动态读取，无需填写。
目标 Wi-Fi 必须已通过 NetworkManager 保存配置及连接凭据。
公开仓库仅保留配置模板，不要提交设备的实际配置或运行日志。

登录板子后运行：

```sh
cd ~/wifi-watchdog
sudo ./install.sh
```

安装会立即启用定时检查；当前系统启动超过 120 秒时，首轮可能立即执行。
重复安装更新程序和服务，但保留已有 `/etc/wifi-watchdog.conf`。
若已安装过，需直接修改 `/etc/wifi-watchdog.conf` 才能更新配置。

确认 `wifi-watchdog.timer` 为 `enabled` 和 `active (waiting)`。
`wifi-watchdog.service` 是单次执行服务，检查后显示 `inactive (dead)` 且
`status=0/SUCCESS` 属于正常现象。等待约一分钟后，再检查最近执行时间是否更新。

## 状态和日志

```sh
systemctl status wifi-watchdog.timer --no-pager
systemctl list-timers wifi-watchdog.timer --all
sudo tail -n 50 /var/lib/wifi-watchdog/events.log
sudo cat /run/wifi-watchdog/failures
sudo journalctl -u wifi-watchdog.service -n 30 --no-pager
```

正常检查没有应用日志。systemd 自身仍会记录服务生命周期；它的日志在本机为易失存储。
应用异常日志直接写入 SD 卡上的 `/var/lib/wifi-watchdog/events.log`，逐条 fsync，
每份最大约 1 MiB，保留 5 份轮转文件，总计约 6 MiB。轮转后删除最旧内容。
失败计数位于 `/run`，跨服务调用保留，重启清零。
网关持续不可达会反复触发每轮开机后的失败计数及重启。

## 配置和维护

配置位于 `/etc/wifi-watchdog.conf`。修改下次执行生效。
更换 Wi-Fi 后需用 `nmcli connection show` 获取新 UUID 并更新配置。
网络维护或主动断开 Wi-Fi 前先停止定时器，避免触发自动恢复：

```sh
sudo systemctl disable --now wifi-watchdog.timer
sudo systemctl stop wifi-watchdog.service
```

重新启用：`sudo systemctl enable --now wifi-watchdog.timer`。
手动停止正在执行的服务可能中断重连，应在本地控制台操作。

卸载（保留异常日志）：

```sh
sudo systemctl disable --now wifi-watchdog.timer
sudo systemctl stop wifi-watchdog.service
sudo rm -f /etc/systemd/system/wifi-watchdog.service /etc/systemd/system/wifi-watchdog.timer
sudo rm -f /usr/local/sbin/wifi-watchdog.py /etc/wifi-watchdog.conf
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

## 验证

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
```

模拟测试不调用真实网络重连或重启。首次部署只做真实健康探测，未主动断网或重启。
