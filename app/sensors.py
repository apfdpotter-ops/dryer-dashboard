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
import os
from typing import Tuple, Optional

# Try to import hardware-specific libraries; if they're not available (e.g. on
# a development machine), provide simulated sensor implementations so the
# Flask server can start without raising ImportError at import-time.
SIMULATED = False
_HW_LIBS_OK = False
_HW_INIT_DONE = False

# Hardware handles (populated by lazy init)
spi = None
cs_inlet = None
cs_outlet = None
thermo_inlet = None
thermo_outlet = None
i2c = None
ads = None
chan_inlet = None
chan_outlet = None

# Try to import hardware-specific libraries but do NOT perform hardware
# initialization at import time. This makes the module safe to import while
# other processes may be using GPIO; actual claim of GPIO happens in
# _init_hardware() which is called once, lazily, from the read functions.
try:
    import board
    import busio
    import digitalio

    import adafruit_max31855
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    _HW_LIBS_OK = True
except Exception as e:
    # Hardware libs not available; we'll run in simulated mode.
    _HW_LIBS_OK = False
    SIMULATED = True
    # don't print noisy traceback here — leave minimal message
    print(f"Hardware sensor libraries not available, running in SIMULATED mode: {e}")


def _init_hardware():
    """Attempt to initialize hardware. On failure we set SIMULATED=True and
    avoid raising so the web server remains available.

    This function is safe to call multiple times; it will try initialization
    only once per process. If initialization fails the first time we fall
    back to simulated mode.
    """
    global _HW_INIT_DONE, SIMULATED
    global spi, cs_inlet, cs_outlet, thermo_inlet, thermo_outlet
    global i2c, ads, chan_inlet, chan_outlet

    if _HW_INIT_DONE:
        return
    _HW_INIT_DONE = True

    if not _HW_LIBS_OK:
        SIMULATED = True
        return

    try:
        # === SPI setup for MAX31855 thermocouples ===
        spi = busio.SPI(clock=board.SCLK, MISO=board.MISO)

        # Chip select pins for each thermocouple. Allow overriding via
        # environment variables CS_INLET_PIN / CS_OUTLET_PIN using the
        # board.<NAME> attribute name (for example: D5, D13, etc.). Default
        # inlet remains D5; outlet defaults to D13 (physical pin 33) since
        # the outlet sensor was moved there.
        inlet_pin_name = os.environ.get('CS_INLET_PIN', 'D5')
        outlet_pin_name = os.environ.get('CS_OUTLET_PIN', 'D13')
        try:
            cs_inlet_pin = getattr(board, inlet_pin_name)
        except Exception:
            cs_inlet_pin = board.D5
        try:
            cs_outlet_pin = getattr(board, outlet_pin_name)
        except Exception:
            cs_outlet_pin = board.D13

        cs_inlet = digitalio.DigitalInOut(cs_inlet_pin)
        cs_outlet = digitalio.DigitalInOut(cs_outlet_pin)

        # Create MAX31855 objects
        thermo_inlet = adafruit_max31855.MAX31855(spi, cs_inlet)
        thermo_outlet = adafruit_max31855.MAX31855(spi, cs_outlet)

        # === I2C setup for ADS1115 (moisture sensors) ===
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)

        # Single-ended channels A0 and A1
        chan_inlet = AnalogIn(ads, ADS.P0)   # A0 = moisture in
        chan_outlet = AnalogIn(ads, ADS.P1)  # A1 = moisture out

        # If we reach here, hardware is usable.
        SIMULATED = False
    except Exception as e:
        # On any hardware error, fall back to simulated readings. Print a
        # concise diagnostic for the journal so the operator can inspect it.
        SIMULATED = True
        import traceback
        print(f"Hardware init failed, falling back to SIMULATED mode: {e}")
        traceback.print_exc()


def c_to_f(celsius: Optional[float]) -> Optional[float]:
    """Convert Celsius to Fahrenheit.

    Returns None when input is None.
    """
    if celsius is None:
        return None
    return (celsius * 9 / 5) + 32


def get_temps(return_fahrenheit: bool = False) -> Tuple[Optional[float], Optional[float]]:
    """Return inlet and outlet temperatures.

    By default returns values in °C. If `return_fahrenheit=True` returns
    values converted to °F.
    """
    # Ensure hardware is initialized (lazily). This may set SIMULATED=True on
    # failure which causes the functions to return simulated values.
    try:
        _init_hardware()
    except Exception:
        # _init_hardware prints its own diagnostics; fall back to simulated.
        pass

    if SIMULATED:
        inlet_c = round(random.uniform(20.0, 60.0), 2)
        outlet_c = round(random.uniform(20.0, 60.0), 2)
    else:
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

    if return_fahrenheit:
        return c_to_f(inlet_c), c_to_f(outlet_c)

    return inlet_c, outlet_c


def get_moisture() -> Tuple[Optional[float], Optional[float]]:
    """Return inlet/outlet voltages from ADS1115 (in volts)."""
    try:
        _init_hardware()
    except Exception:
        pass

    if SIMULATED:
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


def read_all() -> dict:
    """Return a comprehensive sensor payload.

    Keys:
      - timestamp (ISO UTC)
      - inlet_c, outlet_c (floats or None)
      - inlet_v, outlet_v (floats or None)
      - simulated (bool)
      - errors (list[str])
    """
    errors = []
    try:
        _init_hardware()
    except Exception as e:
        errors.append(f"hardware init error: {e}")

    inlet_c = outlet_c = None
    try:
        inlet_c, outlet_c = get_temps(return_fahrenheit=False)
    except Exception as e:
        errors.append(f"get_temps error: {e}")

    inlet_v = outlet_v = None
    try:
        inlet_v, outlet_v = get_moisture()
    except Exception as e:
        errors.append(f"get_moisture error: {e}")

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inlet_c": inlet_c,
        "outlet_c": outlet_c,
        "inlet_v": inlet_v,
        "outlet_v": outlet_v,
        "simulated": bool(SIMULATED),
        "errors": errors,
    }


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
