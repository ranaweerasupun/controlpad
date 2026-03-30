# controlpad

A cross-platform Python library for integrating game controllers into robotics,
drone, and edge computing projects.

```python
from controlpad import Gamepad

gp = Gamepad()

@gp.on_axis("left_x", "left_y")
def on_left_stick(x, y):
    robot.set_velocity(x, y)

@gp.on_button_press("cross")
def on_cross():
    robot.jump()

gp.run()
```

---

## Features

- **Event-driven or polling** — use decorator callbacks for clean application code, or poll in your own loop
- **Named axes and buttons** — `state.axis("left_x")` instead of `joystick.get_axis(0)`
- **Built-in profiles** — DualSense and Xbox out of the box; custom profiles in a few lines
- **Auto-detection** — profile is selected automatically from the controller's name string
- **Radial deadzone** — circular 2D deadzone for sticks, not a square
- **Expo curves** — standard RC-style centre softening for precise control
- **Smoothing** — configurable EMA low-pass filter to reduce stick jitter
- **Auto-reconnect** — survives USB wobbles and Bluetooth drops without crashing your application
- **Headless Linux support** — evdev backend requires no display, works inside ROS nodes and Docker containers
- **CLI tools** — `controlpad detect`, `controlpad monitor` for quick diagnostics

---

## Installation

```bash
python3 -m venv my_env 
source my_env/bin/activate 
pip install controlpad
```

For headless Linux (Raspberry Pi, ROS, Docker — no display required):

```bash
python3 -m venv my_env 
source my_env/bin/activate 
pip install "controlpad[evdev]"
```

To check the installed version:

```python
import controlpad
print(controlpad.__version__)   # e.g. "0.1.0"
```

---

## Quick start

### Polling

```python
import time
from controlpad import Gamepad

gp = Gamepad(deadzone=0.08)
gp.connect()

while True:
    state = gp.read()
    print(state.axis("left_x"), state.axis("left_y"))
    print(state.button("cross"))
    print(state.dpad)          # (-1, 0), (0, 1), etc.
    time.sleep(1 / 60)
```

### Event-driven

```python
from controlpad import Gamepad

gp = Gamepad(deadzone=0.08, expo=0.15)

@gp.on_axis("left_x", "left_y")
def on_left_stick(x, y):
    drone.set_velocity(x, y)

@gp.on_axis("r2")           # Trigger: 0.0 → 1.0
def on_throttle(value):
    drone.set_throttle(value)

@gp.on_button_press("triangle")
def take_off():
    drone.take_off()

@gp.on_button_press("cross")
def land():
    drone.land()

@gp.on_disconnect()
def emergency():
    drone.disarm()

gp.run()
```

### Background thread

```python
gp = Gamepad()
thread = gp.run_async()   # Non-blocking — returns immediately

# Your main application continues here
do_other_things()

gp.stop()
thread.join()
```

---

## Configuration

All options are passed to `Gamepad()`:

| Parameter   | Type    | Default  | Description |
|-------------|---------|----------|-------------|
| `profile`   | str or `ControllerProfile` | `None` | Profile name or instance. `None` = auto-detect |
| `index`     | int     | `0`      | Which controller to open if multiple are connected |
| `deadzone`  | float   | `0.05`   | Stick deadzone radius `[0, 1)` |
| `expo`      | float   | `0.0`    | Expo curve strength `[0, 1)`. `0` = linear |
| `smoothing` | float   | `1.0`    | EMA alpha `(0, 1]`. Lower = smoother. `1.0` = off |
| `backend`   | str     | `"auto"` | `"auto"`, `"pygame"`, or `"evdev"` |
| `headless`  | bool    | `False`  | Force SDL dummy video — no display required |
| `reconnect` | bool    | `True`   | Auto-reconnect when controller is lost |
| `poll_rate` | int     | `60`     | Polling frequency in Hz for `run()` |

---

## Custom profiles

If your controller is not auto-detected, define your own profile using
`controlpad detect` to find the raw axis indices first:

```bash
controlpad detect
```

Then define and register the profile:

```python
from controlpad import Gamepad, ControllerProfile, register_profile

my_stick = ControllerProfile(
    name="MyJoystick",
    axis_map={
        "x":        0,
        "y":        1,
        "throttle": 2,
        "twist":    3,
    },
    button_map={
        "trigger": 0,
        "thumb":   1,
    },
    invert_axes={"y"},
    trigger_axes={"throttle"},
)

register_profile(my_stick)

gp = Gamepad(profile="myjoystick")
```

---

## CLI tools

```bash
# Identify your controller and print its full axis/button mapping
controlpad detect

# List all built-in profiles
controlpad list

# Live axis/button stream in the terminal (no display needed)
controlpad monitor
controlpad monitor --rate 50 --deadzone 0.08
```

---

## Headless / Raspberry Pi

On a Raspberry Pi running headless (no desktop), use either:

```python
# Option 1: headless flag
gp = Gamepad(headless=True)
```

```python
# Option 2: evdev backend (no pygame, no SDL)
gp = Gamepad(backend="evdev")
```

```bash
# Option 3: environment variable before import
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
python your_script.py
```

The evdev backend requires `pip install "controlpad[evdev]"` and the user to
be in the `input` group:

```bash
sudo usermod -aG input $USER
```

---

## Supported controllers

| Controller | Profile name | Tested on |
|---|---|---|
| Sony DualSense (CFI-ZCT1W / CFI-ZCT1G) | `dualsense` | Raspberry Pi 5 (Linux), macOS 14 |
| Xbox One / Series X\|S | `xbox` | Linux (xpadneo), macOS |
| Any HID gamepad | `generic` (auto-fallback) | Access axes as `axis_0`, `axis_1`, … |

Contributions for other controllers are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Development setup

Clone the repo and install in editable mode. The `-e` flag is important — it
registers the package with local metadata so `controlpad.__version__`
resolves correctly when running from source.

```bash
git clone https://github.com/ranaweerasupun/controlpad.git
cd controlpad
python3 -m venv my_env 
source my_env/bin/activate 
pip install -e ".[dev]"
```

Run the tests — no controller hardware required, the test suite uses a mock backend:

```bash
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Author

**Supun Sriyananda** — [github.com/ranaweerasupun](https://github.com/ranaweerasupun)