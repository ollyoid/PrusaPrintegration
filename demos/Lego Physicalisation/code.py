import time
import board
import analogio

# Ordered list of days for display
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Map days to pins
pins = {
    "Mon": analogio.AnalogIn(board.IO7),
    "Tue": analogio.AnalogIn(board.IO9),
    "Wed": analogio.AnalogIn(board.IO10),
    "Thu": analogio.AnalogIn(board.IO6),
    "Fri": analogio.AnalogIn(board.IO5),
    "Sat": analogio.AnalogIn(board.IO4),
    "Sun": analogio.AnalogIn(board.IO3)
}

# Thresholds per day (higher voltage = shorter bar)
# Format: list of upper limits (in volts), one per bar length level
# Lower voltages = longer bars
thresholds = {
    "Mon": [2.8, 1.9, 1.6, 1.5, 1.4],
    "Tue": [2.8, 1.9, 1.6, 1.4, 1.2],
    "Wed": [2.8, 1.9, 1.6, 1.3, 1.2],
    "Thu": [2.8, 1.9, 1.6, 1.4, 1.3],
    "Fri": [2.8, 1.9, 1.6, 1.3, 1.2],
    "Sat": [2.8, 1.9, 1.6, 1.45, 1.2],
    "Sun": [2.8, 1.9, 1.6, 1.3, 1.2],
}

def get_voltage(pin):
    """Convert the analog reading (0-65535) to a voltage (0-3.3V)."""
    return (pin.value * 3.3) / 65536

def voltage_to_bar(voltage, limits):
    """Return a bar string based on custom thresholds."""
    for i, limit in enumerate(limits):
        if voltage > limit:
            return "|" * i
    return "|" * (len(limits))

while True:
    print("\n--- Voltage Bar Chart ---")
    for day in days:
        voltage = get_voltage(pins[day])
        bar = voltage_to_bar(voltage, thresholds[day])
        print(f"{day}: {bar:<5} ({voltage:.2f}V)")
    
    time.sleep(0.1
               )