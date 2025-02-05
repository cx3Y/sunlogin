# Sunlogin

本插件可将贝锐向日葵的设备接入HomeAssistant，理论上支持所有插座。

## 已支持型号
- C1
- C1-2
- C1Pro
- C1Pro-BLE
- C2
- C2-BLE
- P1
- P1Pro
- P2
- P4
- P8
- P8Pro

## 安装

### 方法 1：手动安装

1. 下载插件并将 `custom_components/sunlogin` 文件夹复制到 Home Assistant 根目录下的 `custom_components` 文件夹

### 方法 2：通过 HACS 安装

如果你已经安装了 [HACS](https://www.hacs.xyz/docs/use/download/download/)，可以点击下面的按钮快速添加：

[![通过HACS添加集成](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cx3Y&repository=sunlogin&category=integration)

或者，手动添加：

1. 点击右上角的 `Custom repositories`
2. 在弹出的窗口中输入以下信息：
   - **Repository**: `https://github.com/cx3Y/sunlogin`
   - **Type**: `Integration`

## 添加集成

进入 `设置` > `设备与服务` > `添加集成`，并搜索 `sunlogin`

或者，点击下面的按钮直接添加集成：

[![添加集成](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=sunlogin)
