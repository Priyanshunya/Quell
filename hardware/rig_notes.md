# Benchtop Test Rig Notes

The validation setup uses a single-axis linear rail to apply repeatable horizontal wrist accelerations while measuring how much liquid sloshes or spills.

## Subassemblies

- **Tapper Unit:** A small push/pull solenoid mounted beside the vessel holder, driven by a timed 15 ms pulse while the carriage is stationary.
- **Linear-Rail Stage:** A belt- or leadscrew-driven desktop rail controlled by an external stepper/BLDC driver receiving step and direction signals from the `STEVAL-STWINBX1` expansion header.
- **Test Vessels:** Rigid cylindrical containers with clear fill markings (or side-view camera reference) so peak surface displacement can be measured during open-cup runs.

## Wiring and Mechanical Checks

- **Rigid striker mount:** Any play in the solenoid bracket changes impact energy between runs; use a stiff bracket and fixed gap to the container wall.
- **Supply isolation:** Keep solenoid coil and motor driver power on a separate supply rail from the `STEVAL-STWINBX1` sensing domain to avoid switching spikes in the analog mic (`IMP23ABSU`) signal.
- **Flyback protection:** Fit a flyback diode across the solenoid coil right at the driver stage.
