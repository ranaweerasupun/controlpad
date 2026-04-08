"""
controlpad.cli
~~~~~~~~~~~~~~
Command-line tools shipped with the package.

Usage:
    controlpad detect          Identify your controller and print its mapping
    controlpad list            List all built-in profiles
    controlpad monitor         Live axis/button monitor (text, no display needed)
"""

from __future__ import annotations
import sys
import time
import argparse


def cmd_detect(args) -> None:
    """Open the first controller and print its full axis/button map."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from controlpad import Gamepad
    from controlpad.exceptions import NoControllerFound

    print("Scanning for controllers...\n")

    try:
        gp = Gamepad(headless=True)
        name = gp.connect()
    except NoControllerFound as exc:
        print(f"❌  {exc}")
        sys.exit(1)

    profile = gp.profile
    print(f"✅  Controller : {name}")
    print(f"    Profile   : {profile.name}")
    print()

    # Read one frame to get raw counts
    state = gp.read()

    print("─" * 50)
    print(f"{'AXIS':<20} {'INDEX':>5}   CURRENT VALUE")
    print("─" * 50)
    for axis_name, idx in sorted(profile.axis_map.items(), key=lambda x: x[1]):
        val = state.axis(axis_name)
        flags = []
        if axis_name in profile.invert_axes:
            flags.append("inverted")
        if axis_name in profile.trigger_axes:
            flags.append("trigger")
        note = f"  ({', '.join(flags)})" if flags else ""
        print(f"  {axis_name:<18} {idx:>5}   {val:+.4f}{note}")

    print()
    print("─" * 50)
    print(f"{'BUTTON':<20} {'INDEX':>5}   STATE")
    print("─" * 50)
    for btn_name, idx in sorted(profile.button_map.items(), key=lambda x: x[1]):
        pressed = state.button(btn_name)
        mark = "● PRESSED" if pressed else "○"
        print(f"  {btn_name:<18} {idx:>5}   {mark}")

    print()
    gp.disconnect()


def cmd_list(args) -> None:
    """Print all registered profiles."""
    from controlpad.profiles import list_profiles, get_profile

    names = list_profiles()
    print(f"{'PROFILE':<20}  AXES   BUTTONS")
    print("─" * 40)
    for name in names:
        p = get_profile(name)
        print(f"  {p.name:<18}  {len(p.axis_map):>4}   {len(p.button_map):>7}")


def cmd_monitor(args) -> None:
    """
    Live text monitor — streams axis and button state to the terminal.
    No display or pygame window required.
    Press Ctrl-C to exit.
    """
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from controlpad import Gamepad
    from controlpad.exceptions import NoControllerFound

    try:
        gp = Gamepad(headless=True, deadzone=args.deadzone)
        name = gp.connect()
    except NoControllerFound as exc:
        print(f"❌  {exc}")
        sys.exit(1)

    print(f"Monitoring: {name}  (profile: {gp.profile.name})")
    print("Press Ctrl-C to exit.\n")

    interval = 1.0 / args.rate

    try:
        while True:
            t0 = time.monotonic()
            state = gp.read()

            # Build a compact one-line summary
            axes_str = "  ".join(
                f"{k}:{v:+.2f}"
                for k, v in sorted(state.axes.items())
                if abs(v) > 0.01
            )
            btns_str = " ".join(k for k, v in state.buttons.items() if v)
            dpad_str = f"dpad:{state.dpad}" if state.dpad != (0, 0) else ""

            parts = [p for p in [axes_str, btns_str, dpad_str] if p]
            line  = "  |  ".join(parts) if parts else "(all at rest)"

            print(f"\r{line:<80}", end="", flush=True)

            elapsed = time.monotonic() - t0
            sleep   = interval - elapsed
            if sleep > 0:
                time.sleep(sleep)

    except KeyboardInterrupt:
        print("\n\nExiting.")
        gp.disconnect()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="controlpad",
        description="controlpad — game controller tools for robotics and edge computing",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # detect
    p_detect = sub.add_parser("detect", help="Identify connected controller and print mapping")
    p_detect.set_defaults(func=cmd_detect)

    # list
    p_list = sub.add_parser("list", help="List all built-in controller profiles")
    p_list.set_defaults(func=cmd_list)

    # monitor
    p_monitor = sub.add_parser("monitor", help="Live axis/button monitor (text mode)")
    p_monitor.add_argument(
        "--rate", type=int, default=30,
        help="Poll rate in Hz (default: 30)"
    )
    p_monitor.add_argument(
        "--deadzone", type=float, default=0.05,
        help="Deadzone (default: 0.05)"
    )
    p_monitor.set_defaults(func=cmd_monitor)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
