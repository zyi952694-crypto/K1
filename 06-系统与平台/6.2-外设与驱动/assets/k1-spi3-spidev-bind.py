#!/usr/bin/python3
"""Bind only the explicitly configured SPI3 WS2812 device; never transfer data."""
from pathlib import Path
import os
import sys
import time

TARGET = Path('/sys/firmware/devicetree/base/soc/spi@d401c000/led-strip@0')

def main():
    if os.geteuid() != 0:
        raise SystemExit('root is required')
    if not TARGET.is_dir():
        raise SystemExit('SPI3 LED device-tree node is absent; nothing was bound')
    if (TARGET / 'compatible').read_bytes() != b'worldsemi,ws2812\0':
        raise SystemExit('Unexpected compatible; refusing to bind')
    if (TARGET / 'reg').read_bytes() != b'\0\0\0\0':
        raise SystemExit('Unexpected chip-select; refusing to bind')
    matches = []
    for attempt in range(50):
        matches = [p for p in Path('/sys/bus/spi/devices').glob('spi*.*')
                   if (p / 'of_node').resolve() == TARGET.resolve()]
        if matches:
            break
        time.sleep(0.1)
    if len(matches) != 1:
        raise SystemExit(f'Expected one SPI3 LED device, found {len(matches)}')
    device = matches[0]
    controller_node = device.resolve().parent / 'of_node'
    if controller_node.resolve() != TARGET.parent.resolve():
        raise SystemExit('SPI controller does not match SPI3; refusing to bind')
    driver = device / 'driver'
    if driver.exists():
        if driver.resolve().name != 'spidev':
            raise SystemExit('Device already has another driver; refusing to unbind')
    else:
        (device / 'driver_override').write_text('spidev\n')
        Path('/sys/bus/spi/drivers/spidev/bind').write_text(device.name + '\n')
    if not driver.exists() or driver.resolve().name != 'spidev':
        raise SystemExit('spidev binding failed')
    print(f'Bound {device.name} to spidev; no SPI transfer performed')

if __name__ == '__main__':
    main()
