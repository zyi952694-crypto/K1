---
sidebar_position: 0
slug: /k1/FAQ
---

# FAQ

## 登录

### 普通用户忘记密码怎么解决？

1. 开机进入登录界面。
2. 按下 **Ctrl + Alt + F3**，进入 tty3 终端。使用功能键需要 Fn 的键盘，先锁定 Fn 或同时按下 Fn。
3. 输入用户名 `root` 和密码。保留初始密码的系统可使用 `bianbu` 登录。
4. 运行 `export LANG=en_US.UTF-8`，临时修改终端语言，避免乱码。
5. 运行 `passwd 用户名` 修改密码，例如 `passwd bianbu`。
6. 按下 **Ctrl + Alt + F1**，切回登录界面并使用新密码登录。

## 系统升级

### 已有 Bianbu 2.2 项目需要升级吗？

已有项目保留配套的 Bianbu 2.2 / ROS2_LXQT 系统和运行库。新 SDK 使用独立的 Bianbu 2.3.5 环境；已有系统按需升级，具体步骤和 BROS 运行库要求见 [2.3 系统升级](02-快速入门/2.3-系统升级.md)。

### 升级提示有未完成的软件包更新怎么办？

按 [2.3 系统升级 · 安装系统更新](02-快速入门/2.3-系统升级.md#3-安装系统更新)检查待升级清单和依赖状态。LXQt 文件管理器相关包出现文件覆盖冲突时，参见该章的[软件包冲突处理](02-快速入门/2.3-系统升级.md#5-lxqt-文件管理器软件包冲突)。

## 问题反馈

1. [gitee提交issues](https://gitee.com/bianbu/brdk-doc/issues)
2. [开发者论坛](https://forum.spacemit.com/)
