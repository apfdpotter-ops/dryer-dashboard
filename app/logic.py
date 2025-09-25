"""
logic.py
---------
Handles conversions and calculations for dryer data:
- Celsius → Fahrenheit
- Volts → Moisture %
- Adds dummy bushels/hr value
"""

from app.sensors import get_temps, get_moisture
import random


def c_to_f(celsius):
    """Convert Celsius to Fahrenheit."""
    if celsius is None:
        return None
    return (celsius * 9 / 5) + 32


def volts_to_moisture(volts):
    """
    Convert sensor voltage to % moisture.
    NOTE: Placeholder formula for now.
    - Assume 0.0 V = 0% moisture
    - Assume 3.3 V = 35% moisture
    """
    if volts is None:
        return None
    moisture_pct = (volts / 3.3) * 35.0
    return round(moisture_pct, 2)


def get_processed_data():
    """Read raw sensors and return converted values."""
    inlet_c, outlet_c = get_temps()
    inlet_v, outlet_v = get_moisture()

    data = {
        "inlet_temp_F": round(c_to_f(inlet_c), 2) if inlet_c is not None else None,
        "outlet_temp_F": round(c_to_f(outlet_c), 2) if outlet_c is not None else None,
        "inlet_moisture_pct": volts_to_moisture(inlet_v),
        "outlet_moisture_pct": volts_to_moisture(outlet_v),
        # dummy bushels/hr for now
        "bushels_per_hr": random.randint(500, 800)
    }

    return data


if __name__ == "__main__":
    # Simple test
    print("Testing processed logic… Press Ctrl+C to stop.")
    import time
    while True:
        print(get_processed_data())
        time.sleep(5)
