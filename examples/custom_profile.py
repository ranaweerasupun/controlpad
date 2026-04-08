"""
Custom profile example — define your own controller mapping.

Run axis_mapper.py (from the companion tools) to discover axis indices
for any controller not already supported, then register it here.
"""

from controlpad import Gamepad, ControllerProfile, register_profile

# Define a profile for a hypothetical generic USB joystick
my_joystick = ControllerProfile(
    name="MyJoystick",
    axis_map={
        "x":     0,
        "y":     1,
        "twist": 2,
        "throttle": 3,
    },
    button_map={
        "trigger": 0,
        "thumb":   1,
        "btn_3":   2,
        "btn_4":   3,
    },
    invert_axes={"y"},          # Screen Y is inverted; fix it here
    trigger_axes={"throttle"},  # Normalise to [0, 1]
)

# Register so it's available by name in any Gamepad() call
register_profile(my_joystick)

gp = Gamepad(profile="myjoystick", deadzone=0.05)

@gp.on_axis("x", "y")
def on_stick(x, y):
    print(f"Stick x={x:+.2f}  y={y:+.2f}")

@gp.on_button_press("trigger")
def fire():
    print("Fire!")

gp.run()
