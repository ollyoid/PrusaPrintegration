# controller.py
import time
import board
import touchio
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# BLE setup
ble = BLERadio()

# Touch sensors
touch_up = touchio.TouchIn(board.IO7)
touch_down = touchio.TouchIn(board.IO6)
touch_up.threshold = 40000
touch_down.threshold = 40000

# Track previous touch state
was_touched_up = False
was_touched_down = False

def connect_to_dongle():
    print("Scanning for dongle...")
    for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
        if UARTService in adv.services:
            ble.stop_scan()
            try:
                connection = ble.connect(adv)
                print("Connected to dongle!")
                return connection
            except Exception as e:
                print(f"Connection failed: {e}")
    ble.stop_scan()
    return None

# Main loop
uart_connection = None
uart = None

while True:
    if not uart_connection or not uart_connection.connected:
        uart_connection = connect_to_dongle()
        if uart_connection and UARTService in uart_connection:
            uart = uart_connection[UARTService]
        else:
            time.sleep(1)
            continue

    # If we get here, we're connected and ready to send
    now_up = touch_up.value
    if now_up and not was_touched_up:
        uart.write("UP\n")
        print("Sent: UP")
    elif not now_up and was_touched_up:
        uart.write("RELEASE_UP\n")
        print("Sent: RELEASE_UP")
    was_touched_up = now_up

    now_down = touch_down.value
    if now_down and not was_touched_down:
        uart.write("DOWN\n")
        print("Sent: DOWN")
    elif not now_down and was_touched_down:
        uart.write("RELEASE_DOWN\n")
        print("Sent: RELEASE_DOWN")
    was_touched_down = now_down

    time.sleep(0.01)