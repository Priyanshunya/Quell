# Slosh Frequency and Three-Impulse ZVD Notes

When a liquid-filled container accelerates suddenly, the free surface oscillates at its fundamental slosh frequency. If the motion planner ignores this mode, waves build up and spill.

## Fundamental Slosh Frequency in a Cylinder

For an upright rigid cylindrical container of inner radius $R$ and liquid depth $h$ under gravity $g$, the lowest antisymmetric slosh frequency (in Hz) is approximated by:

$$f_n = \frac{1}{2\pi}\sqrt{\frac{1.841\,g}{R}\tanh\!\left(\frac{1.841\,h}{R}\right)}, \qquad \omega_n = 2\pi f_n$$

## Three-Impulse ZVD Input Shaper

Instead of commanding one abrupt velocity step, a ZVD shaper splits the command into three scaled impulses spaced across one damped slosh period $T_d$:

$$T_d = \frac{2\pi}{\omega_n\sqrt{1-\zeta^2}}, \qquad K = e^{-\zeta\pi/\sqrt{1-\zeta^2}}$$

The impulse amplitudes and application times are:

$$A_1 = \frac{1}{(1+K)^2}, \qquad A_2 = \frac{2K}{(1+K)^2}, \qquad A_3 = \frac{K^2}{(1+K)^2}$$

$$t_1 = 0, \qquad t_2 = \frac{T_d}{2}, \qquad t_3 = T_d$$

For lightly damped water ($\zeta \approx 0$, $K \approx 1$), the weights simplify to:

$$A_1 = 0.25, \qquad A_2 = 0.50, \qquad A_3 = 0.25$$

## Why Coarse Fill Buckets Are Enough

A single mechanical tap on an opaque container will not tell us the exact liquid height to the millimeter. Because a ZVD shaper sets both residual vibration and its slope with respect to frequency to zero at the design frequency, it tolerates roughly ±14% error in $f_n$ while still keeping residual wave amplitude low. Grouping containers into coarse fill states is therefore enough to pick an effective ZVD profile.
