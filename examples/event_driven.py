"""
Event-driven example — register callbacks and call gp.run().
Ideal for applications where the controller drives the control loop.
"""

from controlpad import Gamepad

gp = Gamepad(deadzone=0.08, expo=0.15, poll_rate=60)


@gp.on_axis("left_x", "left_y")
def on_left_stick(x, y):
    if abs(x) > 0.01 or abs(y) > 0.01:
        print(f"Left stick  → x={x:+.2f}  y={y:+.2f}")


@gp.on_axis("right_x", "right_y")
def on_right_stick(x, y):
    if abs(x) > 0.01 or abs(y) > 0.01:
        print(f"Right stick → x={x:+.2f}  y={y:+.2f}")


@gp.on_axis("l2")
def on_left_trigger(value):
    if value > 0.02:
        print(f"L2 trigger  → {value:.2f}")

@gp.on_button_press("l1")
def on_l1():
    print("L1 pressed")

@gp.on_button_press("r1")
def on_r1():
    print("R1 pressed")


@gp.on_axis("r2")
def on_r2(value):
    if value > 0.02:   # small threshold to ignore noise at rest
        print(f"R2 trigger → {value:.2f}")



@gp.on_button_press("cross")
def on_cross():
    print("✕  Cross pressed")


@gp.on_button_press("circle")
def on_circle():
    print("○  Circle pressed")


@gp.on_button_press("triangle")
def on_triangle():
    print("△  Triangle pressed")


@gp.on_button_press("square")
def on_square():
    print("□  Square pressed")


@gp.on_button_press("options")
def on_options():
    print("Options pressed — stopping.")
    gp.stop()


@gp.on_connect()
def on_connect(name):
    print(f"Controller connected: {name}")


@gp.on_disconnect()
def on_disconnect():
    print("Controller disconnected!")


print("Press Options button or Ctrl-C to exit.\n")
gp.run()
