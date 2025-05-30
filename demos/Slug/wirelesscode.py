import time
import board
import touchio

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# BLE setup
hid = HIDService()
ble = BLERadio()
advertisement = ProvideServicesAdvertisement(hid)
keyboard = Keyboard(hid.devices)

# Touch pins setup
touch_up = touchio.TouchIn(board.IO7)
touch_down = touchio.TouchIn(board.IO6)
touch_up.threshold = 40000
touch_down.threshold = 40000

# Track previous touch states
was_touched_up = False
was_touched_down = False

# Advertise
ble.start_advertising(advertisement)
print("Waiting for connection...")

while True:

    while not ble.connected:
        pass

    print("Connected!")

    # Main loop
    while ble.connected:
        # Check UP pin
        now_up = touch_up.value
        if now_up and not was_touched_up:
            print("UP touched")
            keyboard.press(Keycode.UP_ARROW)
        elif not now_up and was_touched_up:
            print("UP released")
            keyboard.release(Keycode.UP_ARROW)
        was_touched_up = now_up

        # Check DOWN pin
        now_down = touch_down.value
        if now_down and not was_touched_down:
            print("DOWN touched")
            keyboard.press(Keycode.DOWN_ARROW)
        elif not now_down and was_touched_down:
            print("DOWN released")
            keyboard.release(Keycode.DOWN_ARROW)
        was_touched_down = now_down

        time.sleep(0.01)  # Small delay for responsiveness
