# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Two Touch Pin Example - Print to the serial console when a pin is touched.
"""
import time
import random
import board
import touchio

import usb_midi

import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

print(usb_midi.ports)
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)
print("Midi test")
# Convert channel numbers at the presentation layer to the ones musicians use
print("Default output channel:", midi.out_channel + 1)
print("Listening on input channel:", midi.in_channel + 1)


touch_pins = [touchio.TouchIn(getattr(board, f"IO{i}")) for i in range(1, 10)]

for pin in touch_pins:
    pin.threshold = 40000
    
touch_states = [False for pin in touch_pins]
note_states = [False for pin in touch_pins]
note_last_registered = [0 for pin in touch_pins]

midi_map = ["A3", "C4", "D4", "E4", "G4", "A4", "C5", "D5"]
    

while True:
    t = time.monotonic()
    for i, note in enumerate(note_states):
        if note:
            if t - note_last_registered[i] >0.2:
                midi.send(NoteOff(midi_map[i-1], 120))
                note_states[i] = False
    for i, touch in enumerate(touch_pins):
        if touch.value:
            if not touch_states[i]:
                print(f"Pin {i+1} touched!")
                touch_states[i] = True
                print(midi_map[i-1])
                midi.send(NoteOn(midi_map[i-1], 120))
                note_states[i] = True
            note_last_registered[i] = t
        else:
            touch_states[i] = False