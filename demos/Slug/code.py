import time
import board
import touchio

touch_pins = [touchio.TouchIn(getattr(board, f"IO{i}")) for i in [10,9]]

for pin in touch_pins:
    pin.threshold = 30000

    
while True:
    for pin in touch_pins:
        print(pin.raw_value)
    time.sleep(0.1)
        