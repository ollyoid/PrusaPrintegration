import time
import board
import rp2pio
import adafruit_pioasm
import array
import memorymap
import busio
import adafruit_drv2605
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# Enable pull-up resistor manually
def enable_pullup_gpio(pin_number):
    pads_bank0_base = 0x4001C000
    gpio_base_offset = 0x04
    gpio_offset = gpio_base_offset + (pin_number * 4)
    pad_address = pads_bank0_base + gpio_offset

    pads_bank0 = memorymap.AddressRange(start=pad_address, length=4)
    pad_ctrl = int.from_bytes(pads_bank0[:4], "little")
    pad_ctrl &= ~(1 << 2)
    pad_ctrl |= (1 << 3)
    pads_bank0[:4] = pad_ctrl.to_bytes(4, "little")

# PIO capacitive sensing program
capsense = """
.program capsense
loop:
    mov x, ~null
    set pindirs, 1
    set pins, 0
    pull
    set pindirs 0
poll:
    jmp pin report
    jmp x-- poll
report:
    mov isr, x
    push
"""
assembled = adafruit_pioasm.assemble(capsense)

def read_cap_val(pin_val, pin):
    sm = rp2pio.StateMachine(
        assembled,
        frequency=0,
        first_set_pin=pin,
        first_in_pin=pin,
        jmp_pin=pin
    )
    enable_pullup_gpio(pin_val)
    buffer = array.array('I', [0])
    sm.write(bytes((1,)))
    sm.readinto(buffer, end=4)
    sm.deinit()
    return buffer[0]

# Pin configuration: (GPIO Number, board Pin, Label, Action Type, Action Code(s))
# 'type': either "keyboard" or "consumer"
pin_info = [
    (6, board.GP6, "+", "keyboard", [Keycode.KEYPAD_PLUS]),
    (9, board.GP9, "Vol+", "consumer", ConsumerControlCode.VOLUME_INCREMENT),
    (15, board.GP15, "Fast Forward", "consumer", ConsumerControlCode.SCAN_NEXT_TRACK),
    (17, board.GP17, "Play/Pause", "consumer", ConsumerControlCode.PLAY_PAUSE),
    (20, board.GP20, "Rewind", "consumer", ConsumerControlCode.SCAN_PREVIOUS_TRACK),
    (26, board.GP26, "Vol-", "consumer", ConsumerControlCode.VOLUME_DECREMENT),
    (29, board.A3, "-", "keyboard", [Keycode.KEYPAD_MINUS])
]

# Init I2C and DRV2605 haptic driver
i2c = busio.I2C(board.GP3, board.GP2)
drv = adafruit_drv2605.DRV2605(i2c)
drv.use_LRM()

# Init keyboard and consumer control
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
consumer_control = ConsumerControl(usb_hid.devices)

# Get baseline values
initial_vals = [read_cap_val(pin_val, pin) for pin_val, pin, _, _, _ in pin_info]

# Touch detection loop
while True:
    for i, (pin_val, pin, name, action_type, action_data) in enumerate(pin_info):
        val = read_cap_val(pin_val, pin)
        if initial_vals[i] - val > 10:
            print(f"Touched: {name}")
            if action_type == "keyboard":
                keyboard.send(*action_data)
            elif action_type == "consumer":
                consumer_control.press(action_data)
                time.sleep(0.1)
                consumer_control.release()
            # Optional: play haptic effect
            # drv.set_waveform(0, 1)
            # drv.set_waveform(1, 0)
            # drv.go()
            time.sleep(0.1)  # debounce
