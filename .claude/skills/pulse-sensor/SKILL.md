# PulseSensor Playground for Arduino (v2.1.0)

Arduino library for optical heart rate sensors. Provides beat detection, BPM calculation, IBI measurement, LED sync, serial output, and multi-sensor support.

**NOTE**: The Arduino code in the references directory is *indicative only*. Do not use it verbatim in PlatformIO projects - adapt it to PlatformIO's library structure and conventions.

**Wiring**: Purple→A0, Red→5V, Black→GND | **Sample Rate**: 500Hz (2ms)
**Troubleshooting**: Adjust pressure (not too hard/soft), increase threshold if too many false beats, decrease if no detection

## Core Library API

<details>
<summary>Main Classes and Headers</summary>

**PulseSensorPlayground.h** - Manager class: `PulseSensorPlayground(n)`, `begin()`, `analogInput(pin, idx)`, `blinkOnPulse(pin, idx)`, `fadeOnPulse(pin, idx)`, `setThreshold(value, idx)` (default ~550), `sawStartOfBeat(idx)`, `isInsideBeat(idx)`, `getBeatsPerMinute(idx)`, `getInterBeatIntervalMs(idx)`, `getLatestSample(idx)` (0-1023), `pause()`/`resume()`

**PulseSensor.h** - Beat detection algorithm, peak/trough detection, threshold adaptation

**Utility**: `PulseSensorSerialOutput` (serial plotter/Processing output), `PulseSensorTimingStatistics` (performance), `SelectTimer` (platform timers), `TimerHandler` (interrupts)

</details>

## Example Projects

### Getting Started

<details>
<summary>Basic Examples</summary>

**GettingStartedProject.ino** - Direct `analogRead()`, basic threshold, LED blink, serial output (signal testing)
**Getting_BPM_to_Monitor.ino** - Library-based BPM/IBI to serial monitor
**PulseSensor_BPM.ino** - Full-featured: hardware/software timer, plotter/visualizer, blink/fade

</details>

### Output Devices

<details>
<summary>Speaker, Servo, LED Matrix</summary>

**PulseSensor_Speaker.ino** - Beep on heartbeat using `tone()`
**PulseSensor_Servo_Motor.ino** - Servo control synced to pulse, amplitude→angle mapping
**PulseSensor_UNO_R4_WiFi_LEDmatrix_Heartbeat.ino** - Animated heart icon on UNO R4 WiFi matrix
**PulseSensor_UNO_R4_WiFi_LEDmatrix_Plotter.ino** - Waveform display on LED matrix

</details>

### Advanced Features

<details>
<summary>Multi-Sensor and Timing</summary>

**TwoPulseSensors_On_OneArduino.ino** - `PulseSensorPlayground(2)`, independent BPM per sensor
**PulseSensor_Pulse_Transit_Time.ino** - Measure pulse transit time between two body locations

</details>

### Platform-Specific

<details>
<summary>Different Microcontrollers</summary>

**PulseSensor_ESP32.ino** - ESP32 hardware timer configuration
**PulseSensor_ATtiny85_Serial.ino** - ATtiny85 with software serial
**PulseSensor_ATtiny85_noSerial.ino** - ATtiny85 minimal (LED only, no serial)
**PulseSensor_nRF52_Heartrate_Monitor_Service.ino** - BLE heart rate service (Adafruit nRF52)
**SoftwareSerialDemo.ino** - SoftwareSerial usage example

</details>

### Testing

**PulseSensorLIbrary_V2_System_Test.ino** - Complete library test with diagnostics
**serialStuff.ino** - Helper functions for system test
