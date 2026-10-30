# K1 MUSE Pi Pro SPI3 与 spidev 配置

本说明用于 [LED 章节](../6.2.9-LED.md) 的 SPI 前置配置。若系统已提供排针对应的可用 `/dev/spidev3.0`，无需重复配置。

适用对象为 K1 MUSE Pi Pro 和厂商 K1 Linux 6.6 设备树。SPI3 控制器路径为 `/soc/spi@d401c000`，排针使用 `pinctrl_ssp3_0`。其他板型或内核版本需核对相应源码、启动 DTB 和引脚定义。

## 1. 检查接口与内核

```bash
uname -a
ls -l /dev/spidev* 2>/dev/null
ls /sys/class/spi_master/
ls /sys/bus/spi/devices/
grep -E 'CONFIG_SPI_K1X=|CONFIG_SPI_SPIDEV=|CONFIG_MODULES=|CONFIG_MODVERSIONS=' \
    "/boot/config-$(uname -r)"
```

要生成 `/dev/spidev3.0`，需要满足三个条件：

1. SPI3 控制器启用，并选择正确的排针复用功能。
2. 设备树声明 SPI3 下的目标从设备。
3. `spidev` 驱动可用，并绑定该从设备。

`CONFIG_SPI_K1X=y` 只代表控制器驱动可用。仅有 `spi4.0` 也不代表排针 SPI3 可用；MUSE Pi Pro 的 `spi4.0` 用于板载 NOR Flash，不要将它解绑或用于 LED 测试。

以下配置会启用 SPI3，并停用与其物理针脚 23、24 冲突的普通 CAN。修改前断开这组排针上的外设，完成重启和节点检查后，再断电接入灯带。

## 2. 准备 spidev 驱动

如果运行内核已启用 `CONFIG_SPI_SPIDEV=y`，不需要编译额外模块；若为 `m` 且配套模块已安装，执行 `sudo modprobe spidev` 即可。否则，可在匹配的内核源码中启用 `CONFIG_SPI_SPIDEV=m` 或 `y`，按 [官方内核编译指南](https://github.com/spacemit-com/docs-bianbu/blob/main/zh/development/kernel_compile.md) 构建与安装。

对于已有匹配内核开发包且支持模块加载的系统，也可以单独编译 `spidev.ko`。下面给出已在 **内核包 `6.6.63-2.2.9.2`、RISC-V、GCC 13.2** 环境使用的源码与构建方法。它不要求重编内核镜像，但不能将编译后的 `.ko` 直接套用到其他内核。

先核对内核、开发包和构建目录：

```bash
dpkg-query -W "linux-image-$(uname -r)" "linux-headers-$(uname -r)"
readlink -f "/lib/modules/$(uname -r)/build"
gcc --version
```

开发包必须与运行内核匹配；若未安装，先从该系统对应的软件源或镜像配套包取得匹配版本。不要仅凭 `uname -r` 相同判定兼容。启用 `CONFIG_MODVERSIONS` 的内核还需要匹配的 `Module.symvers`。

在上述 `6.6.63-2.2.9.2` 环境，可执行：

```bash
mkdir -p ~/k1-spidev-module
cd ~/k1-spidev-module
wget -O spidev.c \
    https://raw.githubusercontent.com/spacemit-com/linux-6.6/0faf1c69bee4b0fa98940e453eeb90494effa342/drivers/spi/spidev.c
printf '%s\n' 'b0dcebf931dbeb542fa5916c5492aaaefb2224230a41efc52dce489758dfab90  spidev.c' | sha256sum -c -
printf '%s\n' 'obj-m += spidev.o' > Makefile
make -C "/lib/modules/$(uname -r)/build" M="$PWD" modules -j2
modinfo ./spidev.ko
```

确认构建成功且版本匹配后，安装并加载：

```bash
sudo install -D -m 644 spidev.ko \
    "/lib/modules/$(uname -r)/extra/spidev.ko"
sudo depmod -a "$(uname -r)"
sudo modprobe spidev
```

若提示 `invalid module format` 或符号不匹配，应重新核对开发包、配置及编译器，不要强制加载。此方法不修改 `spidev.c`，也不改变已安装的 `/boot/config-*` 文件；加载后可通过 `/sys/module/spidev` 检查实际状态。

## 3. 配置 SPI3 与从设备

使用与目标系统匹配的厂商内核源码，在板级文件 `arch/riscv/boot/dts/spacemit/k1-x_MUSE-Pi-Pro.dts` 中合并下列配置。修改现有 `&spi3` 节点并添加子节点；若已有相同片选的设备，应先核对用途，不要重复声明。保留板级文件中的其他属性。

```dts
&flexcan0 {
    status = "disabled";
};

&spi3 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ssp3_0>;
    k1x,ssp-disable-dma;
    k1x,ssp-clock-rate = <25600000>;
    status = "okay";

    led-strip@0 {
        compatible = "worldsemi,ws2812";
        reg = <0>;
        spi-max-frequency = <6400000>;
        status = "okay";
    };
};
```

`worldsemi,ws2812` 在这里用于标识用户态灯带适配设备，并非该内核中可自动匹配 `spidev` 的设备树绑定。第 4 步通过标准 `driver_override` 接口显式绑定，不需要修改驱动匹配表。不要改为 `compatible = "spidev"`，该内核不支持这种通用声明。

按照官方内核编译指南准备构建依赖和匹配的源码。在 **K1 板端的该内核源码根目录**，使用当前系统配置构建设备树：

```bash
cp "/boot/config-$(uname -r)" .config
make ARCH=riscv olddefconfig
make ARCH=riscv dtbs -j2
ls -l arch/riscv/boot/dts/spacemit/k1-x_MUSE-Pi-Pro.dtb
```

这是设备树构建，不安装内核镜像。若在 PC 交叉编译，需按官方指南设置工具链和 `CROSS_COMPILE`，不能直接照搬板端命令。

**部署时必须确认系统实际加载的 DTB 路径。** 某些 Bianbu 6.6.63 系统使用 `/boot/spacemit/6.6.63/k1-x_MUSE-Pi-Pro.dtb`；其他版本应检查 GRUB、extlinux 或实际启动配置，不要只因同名文件存在就认定它正在使用。

以下命令只用于已确认采用该目录布局的系统，在上述内核源码根目录执行。先备份，再替换；若 `.before-led` 已存在，命令会停止，应先核对已有备份，或另选备份名称并同步调整恢复步骤。

```bash
led_dtb="/boot/spacemit/$(uname -r)/k1-x_MUSE-Pi-Pro.dtb"
# 任一命令失败时停止，不继续重启。
test -f "$led_dtb" &&
    test ! -e "${led_dtb}.before-led" &&
    sudo cp -a "$led_dtb" "${led_dtb}.before-led" &&
    sudo install -m 644 arch/riscv/boot/dts/spacemit/k1-x_MUSE-Pi-Pro.dtb "$led_dtb" &&
    sync
```

确认备份存在、部署成功后重启：

```bash
sudo reboot
```

重新登录后检查：

```bash
tr -d '\0' < /sys/firmware/devicetree/base/soc/spi@d401c000/status
ls -l /sys/bus/spi/devices/spi3.0/of_node
```

预期 SPI3 状态为 `okay`，`spi3.0/of_node` 指向 `led-strip@0`。此时若还没有 `/dev/spidev3.0`，继续完成绑定。

## 4. 绑定 spidev 并设置开机加载

下载随本文提供的两个文件，保存到 K1 的同一目录：

- [k1-spi3-spidev-bind.py](k1-spi3-spidev-bind.py)
- [k1-spi3-spidev.service](k1-spi3-spidev.service)

在保存目录执行：

```bash
sudo install -m 755 k1-spi3-spidev-bind.py /usr/local/sbin/k1-spi3-spidev-bind
sudo install -m 644 k1-spi3-spidev.service /etc/systemd/system/k1-spi3-spidev.service
sudo systemctl daemon-reload
sudo systemctl enable --now k1-spi3-spidev.service
systemctl status k1-spi3-spidev.service --no-pager
ls -l /dev/spidev3.0
```

服务先加载 `spidev`，再根据设备树节点寻找对应从设备。绑定脚本核对控制器、设备标识和片选，且拒绝解绑其他驱动；它不发送 SPI 数据。`active (exited)` 是一次性服务执行完成后的正常状态。再次重启后，节点也应自动出现。

脚本使用的是 Linux 标准接口，等效于对已核对的目标设备执行：

```bash
printf 'spidev\n' | sudo tee /sys/bus/spi/devices/spi3.0/driver_override
printf 'spi3.0\n' | sudo tee /sys/bus/spi/drivers/spidev/bind
```

使用服务后无需重复手动绑定。设备编号以本机实际枚举为准；不要把上述命令应用于板载 Flash 或其他已绑定的设备。

完成后返回 [LED 示例](../6.2.9-LED.md)，断电按接线要求连接灯带，再运行演示程序。

## 5. 恢复配置与升级说明

如需恢复修改前的板级配置，可停用服务并还原备份。以下仍以第 3 步确认的启动目录为例：

```bash
sudo systemctl disable --now k1-spi3-spidev.service
led_dtb="/boot/spacemit/$(uname -r)/k1-x_MUSE-Pi-Pro.dtb"
test -f "${led_dtb}.before-led" &&
    sudo cp -a "${led_dtb}.before-led" "$led_dtb" &&
    sync
```

确认恢复成功后重启，原配置在下次启动生效；停用服务本身不会立即恢复排针复用。若无法启动，可在恢复环境挂载 boot 分区，将备份 DTB 还原到原位置。应在替换 DTB 前准备好可用的本地控制台或系统恢复方式。

上述修改仅涉及 K1 板级设备树、匹配的驱动模块及本机开机绑定服务，不要求修改 K1/K3 共用 LED SDK 源码。内核升级后需重新核对启动设备树和模块兼容性，不要继续复用旧 `.ko`。
