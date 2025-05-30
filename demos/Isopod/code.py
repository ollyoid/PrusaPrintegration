import time
import board
import rp2pio
import adafruit_pioasm
import array
import digitalio
import memorymap
import busio
import adafruit_drv2605
import math
import keypad
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard, find_device
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

## We need to set this manually because the PIO state machine setup in Circuit Python doesn't
## want users to set the pins as outputs as well as setting a pullup... but we need to do this
## because magic..
def enable_pullup_gpio(pin_number):
    pads_bank0_base = 0x4001C000
    gpio_base_offset = 0x04  # Starting offset for GPIO0
    gpio_offset = gpio_base_offset + (pin_number * 4)  # Calculate offset for the given pin
    pad_address = pads_bank0_base + gpio_offset
    
    pads_bank0 = memorymap.AddressRange(start=pad_address, length=4)
    
    # Read current pad control value
    pad_ctrl = int.from_bytes(pads_bank0[:4], "little")
    
    # Clear bit 2 (pull-down disable) and set bit 3 (pull-up enable)
    pad_ctrl &= ~(1 << 2)  # Clear bit 2
    pad_ctrl |= (1 << 3)   # Set bit 3
    
    # Write back the modified control value
    pads_bank0[:4] = pad_ctrl.to_bytes(4, "little")


## This PIO Block essentialy Pulls a pin low. Then sets the pin as an input (already having a pullup)
## and waits to see how long it takes to change. The longer it takes, the greater the capacitance
capsense = """
.program capsense

loop:
    mov x, ~null                     ; Fill X with all ones to be a large number
    set pindirs, 1
    set pins, 0
    pull
    set pindirs 0
poll:
    jmp pin report
    jmp x-- poll               ; Empty X until the pin goes high then jump to the report

report:
    mov isr, x
    push 
"""

assembled = adafruit_pioasm.assemble(capsense)

def read_cap_val(pin_val, pin):
    sm = rp2pio.StateMachine(
        assembled,
        frequency=0, #system clock
        first_set_pin=pin,
        first_in_pin=pin,
        jmp_pin=pin
    )
    enable_pullup_gpio(pin_val)
    buffer = array.array('I', [0])
    sm.write(bytes((1,)))
    sm.readinto(buffer, end=4)
    sm.deinit()
    return(buffer[0])

pin_vals = [6, 9, 10, 19]
pins = [board.GP6, board.GP9, board.GP10, board.GP19]

# Initialize I2C bus and DRV2605 module.
i2c = busio.I2C(board.GP3, board.GP2)
drv = adafruit_drv2605.DRV2605(i2c)
drv.use_LRM()

# Initialize keyboard
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)

initial_vals = [0] * len(pins)
# Track the sequence of touches
touch_sequence = []



for i, pin in enumerate(pins):
    initial_vals[i] = read_cap_val(pin_vals[i], pin)

while True:
    current_time = time.monotonic()
    for i, pin in enumerate(pins):
        val = read_cap_val(pin_vals[i], pin)
        if initial_vals[i] - val > 10:  # Touch detected
            print("Touch")