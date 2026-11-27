# Differences from `wlkatapython` 0.1.3

This file compares this SDK with `wlkatapython` 0.1.3, the package WLKATA
publishes on PyPI. It records which of 0.1.3's behaviours this SDK has
adopted, where it still deviates on purpose, and what is still different.

Last updated: 2026-11-27.

Class names differ between the two: `Harobot_UART` / `Miromax_UART` /
`Mirobot_UART` / `MT4_UART` here, `Harobot` / `MiroMax` / `Mirobot` / `MT4` in
0.1.3. Method names are camelCase here (`writeCoordinate`) and snake_case in
0.1.3 (`write_coordinate`).

Nothing below has been checked against a real Harobot or Miromax. The only
hardware captures in this repository are for the Mirobot and the MT4
(`tests/data/`).

## 1. Adopted from 0.1.3

### Status parsing

| Input | Before | Now (same as 0.1.3) |
| --- | --- | --- |
| Miromax pipe format `<Idle\|Cartesian:…\|Angle:…>` | `"parse error"` | parsed |
| State with a sub-state, `Hold:0` / `Hold:1` (pipe format) | `"parse error"` | parsed; `state` is `"Hold:0"` |
| Harobot comma format, no tail | parsed | parsed |
| Any tail after a further `\|` (`\|Ov:50,100,100`, `\|WCO:0,0,0`) | `"parse error"` unless it was built from the characters of `Ov:100,100,100` | ignored |
| Malformed number such as `1.2.3`, `-`, `5.` | accepted | rejected (comma and Mirobot formats) |
| Explicitly signed number such as `+198.670` | rejected | accepted |

Details:

- `Harobot_UART` and `Miromax_UART` share one parser that tries the pipe
  format, then the comma format. Either class reads either format.
- A number is `[-+]?\d+(?:\.\d+)?`. This also applies to the Mirobot status
  line, so it reaches `Mirobot_UART`, `MT4_UART` and `E4_UART`.
- In the pipe format the numbers are picked out of each section one by one,
  as 0.1.3 does, so a trailing comma is fine and at least six Cartesian values
  and six angles are required. A 7th angle that was not sent stays `-1`. The
  spare 7th Cartesian value is dropped in both formats.

### Commands

| Command | Before | Now (same as 0.1.3) |
| --- | --- | --- |
| Harobot homing | `o105={mode}`, no restart | restart (`o100`), 3 s settle, then `$h{mode}`; an invalid mode sends `$h8` |
| Miromax homing | `o105={mode}` | `$h{mode}`, except mode 8 which sends bare `$h`; an invalid mode sends `$h8`; no restart |
| Harobot / Miromax moves | `…F4000` appended | no feed rate: `G07G90X…`, `G01G90X…`, `G09G90X…` |
| Harobot / Miromax zero | `G9 G90 X0 Y0 Z0 A0 B0 C0 F4000` | `G9 G90 X0 Y0 Z0 A0 B0 C0` |
| Harobot / Miromax unknown motion type | linear (`G01`) | fast (`G07`) |
| Miromax `gripper(num, pin=20, speed=5)` | `M67 E0 Q{0, 4, 7.5}` | `M67 E{pin} Q{92.5 − speed}` to open, `Q{92.5 + speed}` to close, `Q92.5` off; pins 20–23, speed clamped to 1–5 |
| Miromax `pump()` | `M67 E0 Q{0, 100, 50}` | not available; see the three methods below |
| Miromax `pumpSuction(num, pin=10)` | — | `M67 E{pin} Q100` to suck, `Q0` off |
| Miromax `pumpGripper(num, pin=10)` | — | `M67 E{pin} Q75` to open, `Q25` to close, `Q0` off |
| Miromax `pumpSoftGripper(num, pin=10)` | — | same output as `pumpGripper` |
| Miromax `pwmWrite(num, pin=10)` | `M67 E0 Q{num}` | `M67 E{pin} Q{num}`; pins 10, 11, 20–25, anything else falls back to 10 |
| Miromax `cancellation()` | `o117` | `!`, poll status until `Hold:0` (or `Idle`), then `%`, then wait for Idle |

A feed rate can still be sent by setting `_FEED_RATE` on a subclass.

## 2. Where the adopted code still deviates

These are inside the areas above, and are kept on purpose so existing callers
of this SDK keep working.

| Topic | This SDK | 0.1.3 |
| --- | --- | --- |
| Harobot / Miromax status dict | includes `pump`, `valve`, `mode`, always `-1` | those keys are absent |
| Parse failure | returns `"parse error"` | raises `StatusError` |
| Miromax `pump()` | raises `NotImplementedError` naming the replacements | the method does not exist |
| Miromax cancel: pause never settles | returns `False`, `%` not sent | raises `TimeoutError`, `%` not sent |
| Miromax cancel: no Idle after `%` | returns `False` | raises `TimeoutError` (returns `False` on Alarm / Hold) |
| Miromax cancel: Idle check | three consecutive Idle reads (`_waitIdlePoll`) | one Idle read |
| Homing after the restart | settles 3 s, drops buffered input, sends the homing command | settles 3 s, waits for the restart's `ok`, sends, then waits for the homing `ok` |

## 3. Not adopted yet

### Commands

| Command | This SDK | 0.1.3 |
| --- | --- | --- |
| Mirobot / MT4 / E4 homing | `o105={mode}`; invalid mode sends `$h` | `$h{mode}`; invalid mode sends `$h8` (Mirobot) or `$h` (MT4 / E4) |
| Harobot `gripper` / `pump` / `pwmWrite` channel | always `E0` | `pin` argument, 0 or 1 |
| Miromax auto tool-changer | none | `auto_swap_end_effector(num)`: `M67 E24 Q0` / `Q100` |
| Controller delay | none | `write_delay(num)`: `G04 P{seconds}`; on Miromax `num` is milliseconds |
| MT4 `getCoordinate(4)` | returns `coordinate_RZ`, which is where the MT4 captures show the flange angle | returns `coordinate_RX`, which those captures show as always 0 |
| Harobot / Miromax `version()` | inherited, looks for `Harobot` / `Miromax` lines | not provided |

### Reply handling

| Behaviour | This SDK | 0.1.3 |
| --- | --- | --- |
| Status query failure | `getStatus()` returns `"error"`, `-1` or `"parse error"`, and `getState()` returns `"-1"`; no retry | retries 3 times, then raises `TimeoutError` or `StatusError` |
| Values after a failed query | `getAngle()`, `getCoordinate()`, `getPump()`, `getMode()` and `mirobot_state_all` still give the last status that parsed | nothing is returned; the query raises |
| Lines before the status line | reads exactly one line | skips `ok` / info lines for up to 1 s |
| Waiting for `ok` | one immediate read; a missing `ok` returns `None` | waits up to 30 s, skipping other lines, then raises `TimeoutError` |
| Motion commands | do not read their `ok`; it stays buffered | every command waits for `ok`, and optionally for Idle |
| Error lines (`E100`–`E118`, `A100`–`A106`, the word "error") | ignored | raise `ProtocolError` |
| Undecodable bytes | `UnicodeDecodeError` | replaced |
| Empty line in reply to `?` | `getStatus()` returns `-1` | skipped while it waits for the status line |
| Wait for Idle | three consecutive Idle reads, each from a status read in that poll; `False` on timeout | one Idle read; raises on timeout, on `Offline`, and by default on `Alarm` / `Hold` |
| Event-mode wait (`setWaitMode("event")`) | waits for the arm to push an Idle status line, in the model's own format | no event mode |
| GPIO read with an empty field (`1,,0,1`) | regex fails | accepted |
| `version()` | either line order; robot line alone is enough | needs the `EXbox` line, then the robot line |

### Transports

| Topic | This SDK | 0.1.3 |
| --- | --- | --- |
| RS485 | address prefix on any transport | dedicated `Rs485` transport: 38400 baud default, one port shared between robots |
| Post-send delay | fixed 0.1 s | 0.1 s or the wire time at the baud rate, whichever is longer; 0.02 s on BLE; adjustable |
