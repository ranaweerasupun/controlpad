"""
Drone control example — maps a DualSense to a typical quadcopter input layout.

  Left stick  Y  → Throttle  (up/down)
  Left stick  X  → Yaw       (rotate left/right)
  Right stick Y  → Pitch     (forward/back)
  Right stick X  → Roll      (lean left/right)
  L1             → Arm motors
  R1             → Disarm motors
  Cross          → Land
  Triangle       → Take off

Replace the DroneInterface stub with your actual MAVLink / SDK calls.
"""

from controlpad import Gamepad
import threading


# ------------------------------------------------------------------
# Stub: replace with your actual drone SDK
# ------------------------------------------------------------------

class DroneInterface:
    def __init__(self):
        self.armed = False

    def arm(self):
        self.armed = True
        print("[Drone] Armed")

    def disarm(self):
        self.armed = False
        print("[Drone] Disarmed")

    def take_off(self):
        print("[Drone] Taking off")

    def land(self):
        print("[Drone] Landing")

    def set_motion(self, throttle, yaw, pitch, roll):
        if self.armed:
            print(
                f"[Drone] throttle={throttle:+.2f}  yaw={yaw:+.2f}  "
                f"pitch={pitch:+.2f}  roll={roll:+.2f}"
            )


# ------------------------------------------------------------------
# Controller setup
# ------------------------------------------------------------------

drone = DroneInterface()

gp = Gamepad(
    profile="dualsense",
    deadzone=0.10,   # Larger deadzone — safer for flying
    expo=0.25,       # Softer centre feel
    smoothing=0.4,   # Light smoothing to dampen stick jitter
    reconnect=True,  # Keep trying if controller drops
    poll_rate=50,    # 50 Hz is plenty for manual control
)


@gp.on_axis("left_y", "left_x", "right_y", "right_x")
def on_sticks(throttle, yaw, pitch, roll):
    drone.set_motion(throttle, yaw, pitch, roll)


@gp.on_button_press("l1")
def arm():
    drone.arm()


@gp.on_button_press("r1")
def disarm():
    drone.disarm()


@gp.on_button_press("triangle")
def take_off():
    drone.take_off()


@gp.on_button_press("cross")
def land():
    drone.land()


@gp.on_button_press("options")
def quit_app():
    print("Exiting.")
    gp.stop()


@gp.on_connect()
def connected(name):
    print(f"Ready — controller: {name}")
    print("L1=arm  R1=disarm  △=take off  ✕=land  Options=quit\n")


@gp.on_disconnect()
def disconnected():
    drone.disarm()
    print("Controller lost — drone disarmed. Reconnecting...")


gp.run()
