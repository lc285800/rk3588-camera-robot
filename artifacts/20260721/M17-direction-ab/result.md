# M17 physical direction A/B result

## Method

The phone marker remained stationary while the mounted camera started from the
observed 90-degree center. Each direction ran for six seconds with the same
bounded 70-110 degree test range, `Kp=4`, and a 3 degree/second output limit.
The first and last ten detected X errors were compared.

## Results

| Direction | Initial mean absolute error | Final mean absolute error | Result |
|---:|---:|---:|---|
| +1 | 0.590 | 0.754 | diverged; camera moved away |
| -1 | 0.185 | 0.035 | converged by approximately 81% |

The valid `-1` run contained 91 detected samples, no reported fault, and a
1.900-1.924ms pulse range. The marker remained detected through the test. PWM
was disabled/unexported and all runtime processes exited afterward.

## Decision

The installed camera/servo assembly must use `direction=-1`. Future direction
checks must use a stationary target and measured error convergence; perceived
relative motion alone is not accepted as evidence.
