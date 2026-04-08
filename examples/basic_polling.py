"""
Basic polling example — read controller state in your own loop.
"""

import time
from controlpad import Gamepad

gp = Gamepad(deadzone=0.08)
gp.connect()

print("Connected:", gp.profile.name)
print("Press Ctrl-C to exit.\n")

try:
    while True:
        state = gp.read()

        lx = state.axis("left_x")
        ly = state.axis("left_y")
        rx = state.axis("right_x")
        ry = state.axis("right_y")
        l2 = state.axis("l2")       # 0.0 → 1.0
        r2 = state.axis("r2")

        print(
            f"\rL({lx:+.2f},{ly:+.2f})  R({rx:+.2f},{ry:+.2f})  "
            f"L2:{l2:.2f}  R2:{r2:.2f}  DPAD:{state.dpad}   ",
            end="",
            flush=True,
        )

        time.sleep(1 / 60)

except KeyboardInterrupt:
    print("\nExiting.")
