"""
sensors.py
------------
Reads raw values from MAX31855 thermocouples and ADS1115 ADC.
- 2x MAX31855 (inlet & outlet temps) on SPI
- ADS1115 for grain moisture sensors (A0 = inlet, A1 = outlet)

Outputs:
- Temps in °C (conversion to °F happens in test loop for now)
- Moisture in volts (conversion to % later in logic.py)
"""

import time
import random

# Try to import hardware-specific libraries; if they're not available (e.g. on
# a development machine), provide simulated sensor implementations so the
# FastAPI server can start without raising ImportError at import-time.
SIMULATED = False
try:
    import board
    import busio
    import digitalio

    import adafruit_max31855
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except Exception as e:
    SIMULATED = True
    print(f"Hardware sensor libraries not available, running in SIMULATED mode: {e}")

if not SIMULATED:
    # === SPI setup for MAX31855 thermocouples ===
    spi = busio.SPI(clock=board.SCLK, MISO=board.MISO)

    # Chip select pins for each thermocouple
    cs_inlet = digitalio.DigitalInOut(board.D5)   # GPIO5 → Pin 29
    cs_outlet = digitalio.DigitalInOut(board.D6)  # GPIO6 → Pin 31

    # Create MAX31855 objects
    thermo_inlet = adafruit_max31855.MAX31855(spi, cs_inlet)
    thermo_outlet = adafruit_max31855.MAX31855(spi, cs_outlet)

    # === I2C setup for ADS1115 (moisture sensors) ===
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)

    # Single-ended channels A0 and A1
    chan_inlet = AnalogIn(ads, ADS.P0)   # A0 = moisture in
    chan_outlet = AnalogIn(ads, ADS.P1)  # A1 = moisture out


def get_temps():
    """Return inlet and outlet temps in °C as a tuple."""
    if SIMULATED:
        # Simulate reasonable temps in °C
        inlet_c = round(random.uniform(20.0, 60.0), 2)
        outlet_c = round(random.uniform(20.0, 60.0), 2)
        return inlet_c, outlet_c

    try:
        inlet_c = thermo_inlet.temperature
    except Exception as e:
        inlet_c = None
        print(f"Error reading inlet thermocouple: {e}")

    try:
        outlet_c = thermo_outlet.temperature
    except Exception as e:
        outlet_c = None
        print(f"Error reading outlet thermocouple: {e}")

    return inlet_c, outlet_c


def get_moisture():
    """Return inlet/outlet voltages from ADS1115 (in volts)."""
    if SIMULATED:
        # Simulate voltages between 0 and 3.3V
        inlet_v = round(random.uniform(0.0, 3.3), 3)
        outlet_v = round(random.uniform(0.0, 3.3), 3)
        return inlet_v, outlet_v

    try:
        inlet_v = chan_inlet.voltage
    except Exception as e:
        inlet_v = None
        print(f"Error reading inlet moisture sensor: {e}")

    try:
        outlet_v = chan_outlet.voltage
    except Exception as e:
        outlet_v = None
        print(f"Error reading outlet moisture sensor: {e}")

    return inlet_v, outlet_v


def c_to_f(celsius):
    """Convert Celsius to Fahrenheit."""
    if celsius is None:
        return None
    return (celsius * 9 / 5) + 32


if __name__ == "__main__":
    # Simple test loop
    print("Testing sensors... Press Ctrl+C to stop.")
    while True:
        temps = get_temps()
        moist = get_moisture()
        print(f"Inlet Temp: {c_to_f(temps[0])} °F | Outlet Temp: {c_to_f(temps[1])} °F")
        print(f"Inlet Moisture: {moist[0]} V | Outlet Moisture: {moist[1]} V")
        print("-" * 40)
        time.sleep(5)
