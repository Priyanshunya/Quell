# System Architecture

Quell is built to run on a single `STEVAL-STWINBX1` board without an external computer or cloud connection. The main goal is keeping sensing, payload classification, and trajectory shaping tight enough to fit inside a compact wrist module.

## Signal and Control Pipeline

1. **Stationary Tap:** Right after grasping a container, the wrist holds still while a small solenoid delivers a repeatable 15 ms tap. Keeping the wrist stationary prevents motor vibration from polluting the acoustic and structural sensors.
2. **Tap Trigger and Capture (`STEVAL-STWINBX1`):**
   - `ISM330DHCX` uses its on-sensor Machine Learning Core (MLC) to detect the tap onset and trigger recording.
   - `IMP23ABSU` (analog MEMS mic, up to 80 kHz) captures the airborne acoustic ring-down through timer-triggered ADC and DMA.
   - `IIS3DWB` (wideband vibrometer, up to 6 kHz) records wall vibration decay over SPI and DMA.
3. **Payload State Classification (`STM32U585AI`):**
   - Sensor data is logged with `FP-SNS-DATALOG2`, configured through `ST AIoT Craft` (`FP-SNS-STAIOTCFT`), and deployed as a quantized INT8 model using `STM32Cube.AI`.
   - Within 250 ms of the tap, the model assigns the container to one of four coarse classes: `empty`, `shallow_liquid`, `medium_high_liquid`, or `solid_granular`.
4. **ZVD Trajectory Shaping:**
   - Using the predicted class and its calibrated slosh dynamics, the MCU computes a three-impulse Zero-Vibration-Derivative (ZVD) velocity profile.
   - Step and direction signals go out over the expansion header to an external motor driver on the linear-rail rig.

## Design Boundaries

- **Offline operation:** All capture, inference, and pulse timing happen on the `STM32U585AI`.
- **Power target:** Keep average sensing, inference, and trajectory-generation power below 200 mW (excluding the solenoid pulse and motor drive stage).
