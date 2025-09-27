#!/usr/bin/env python3
"""
debug_max31855.py
----------------
Diagnostic script to test MAX31855 thermocouple reliability.
Run this on your Raspberry Pi to identify sensor issues.

Usage: python3 tools/debug_max31855.py
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sensors import get_temps, SIMULATED, _init_hardware

def test_sensor_reliability(num_readings=50, delay=1.0):
    """Test sensor readings and report success/failure rates."""
    print(f"Testing MAX31855 reliability with {num_readings} readings...")
    print(f"Delay between readings: {delay}s")
    print("-" * 60)
    
    # Force hardware initialization
    _init_hardware()
    
    if SIMULATED:
        print("WARNING: Running in SIMULATED mode - no actual hardware testing!")
        return
    
    inlet_successes = 0
    outlet_successes = 0
    inlet_failures = 0
    outlet_failures = 0
    
    for i in range(1, num_readings + 1):
        print(f"Reading {i:2d}/{num_readings}: ", end="", flush=True)
        
        inlet_temp, outlet_temp = get_temps()
        
        # Check inlet
        if inlet_temp is not None:
            inlet_successes += 1
            inlet_status = f"✓ {inlet_temp:6.2f}°C"
        else:
            inlet_failures += 1
            inlet_status = "✗ FAILED"
            
        # Check outlet  
        if outlet_temp is not None:
            outlet_successes += 1
            outlet_status = f"✓ {outlet_temp:6.2f}°C"
        else:
            outlet_failures += 1
            outlet_status = "✗ FAILED"
            
        print(f"Inlet: {inlet_status} | Outlet: {outlet_status}")
        
        if i < num_readings:
            time.sleep(delay)
    
    print("-" * 60)
    print("RESULTS:")
    print(f"Inlet Sensor:  {inlet_successes:2d} successes, {inlet_failures:2d} failures ({inlet_successes/(inlet_successes+inlet_failures)*100:5.1f}% success)")
    print(f"Outlet Sensor: {outlet_successes:2d} successes, {outlet_failures:2d} failures ({outlet_successes/(outlet_successes+outlet_failures)*100:5.1f}% success)")
    print()
    
    if inlet_failures > 0 or outlet_failures > 0:
        print("TROUBLESHOOTING TIPS:")
        print("• Check SPI wiring (MISO, SCLK, CS pins)")
        print("• Verify chip select pins match your hardware (CS_INLET_PIN, CS_OUTLET_PIN)")
        print("• Check power supply stability (3.3V)")
        print("• Look for loose connections on MAX31855 breakout boards")
        print("• Try different delay values between readings")
        print("• Check for electrical interference near SPI lines")

def test_different_delays():
    """Test with different delays to find optimal timing."""
    print("Testing different delays between sensor reads...")
    delays = [0.01, 0.05, 0.1, 0.2, 0.5]
    
    for delay in delays:
        print(f"\nTesting with {delay}s delay:")
        successes = 0
        for _ in range(10):
            inlet_temp, outlet_temp = get_temps()
            if inlet_temp is not None and outlet_temp is not None:
                successes += 1
            time.sleep(delay)
        print(f"Success rate: {successes}/10 ({successes*10}%)")

if __name__ == "__main__":
    print("MAX31855 Thermocouple Diagnostic Tool")
    print("=====================================")
    
    # Basic reliability test
    test_sensor_reliability(num_readings=20, delay=0.5)
    
    # Test different timing
    print("\n" + "="*60)
    test_different_delays()