# Changelog

All notable changes to controlpad are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
controlpad uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-03-30

Initial release.

### Added

**Core**
- `Gamepad` class with both polling and event-driven APIs
- `ControllerState` — processed snapshot with named axis/button access
- Auto-connect and auto-reconnect on controller disconnect
- `run()` blocking loop and `run_async()` background thread variant
- `stop()` for clean shutdown from callbacks or other threads

**Profiles**
- `ControllerProfile` dataclass for declaring axis/button layouts
- Built-in profiles: `DualSense`, `Xbox`
- Auto-detection from SDL controller name string
- `build_generic_profile()` fallback for unknown controllers
- `register_profile()` for custom controller mappings
- `get_profile()` / `list_profiles()` registry API

**Filters**
- `apply_deadzone()` — per-axis deadzone with rescaling
- `apply_deadzone_2d()` — radial (circular) deadzone for sticks
- `apply_expo()` — exponential centre-softening curve
- `ExponentialSmoother` — low-pass EMA filter for axis jitter

**Backends**
- `PygameBackend` — works on Linux, macOS, Windows (requires display or dummy mode)
- `EvdevBackend` — Linux headless backend, no display required (`pip install controlpad[evdev]`)
- Auto backend selection: evdev on headless Linux, pygame elsewhere

**CLI**
- `controlpad detect` — identify controller and print full axis/button map
- `controlpad list` — list all registered profiles
- `controlpad monitor` — live text-mode axis/button stream

**Examples**
- `basic_polling.py` — manual polling loop
- `event_driven.py` — decorator-based callbacks
- `drone_control.py` — full drone input mapping example
- `custom_profile.py` — registering a custom controller layout

---

[Unreleased]: https://github.com/ranaweerasupun/controlpad/compare/v0.1.0...HEAD
[0.1.0]:      https://github.com/ranaweerasupun/controlpad/releases/tag/v0.1.0
