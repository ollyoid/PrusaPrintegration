import usb_hid, usb_midi

# On some boards, we need to give up HID to accomodate MIDI.
usb_hid.disable()
usb_midi.enable()