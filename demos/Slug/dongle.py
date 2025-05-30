# dongle.py
import time
import usb_hid
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

kbd = Keyboard(usb_hid.devices)

ble.start_advertising(advertisement)
print("Advertising as BLE dongle...")

while True:
    if not ble.connected:
        continue

    while ble.connected:
        if uart.in_waiting:
            command = uart.readline().decode("utf-8").strip()
            print(f"Received: {command}")

            if command == "UP":
                kbd.press(Keycode.UP_ARROW)
            elif command == "RELEASE_UP":
                kbd.release(Keycode.UP_ARROW)
            elif command == "DOWN":
                kbd.press(Keycode.DOWN_ARROW)
            elif command == "RELEASE_DOWN":
                kbd.release(Keycode.DOWN_ARROW)
        time.sleep(0.01)
