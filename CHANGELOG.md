# Changelog

All notable changes to controlpad are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
controlpad uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.3.0] — 2026-04-08

### Added

**Output Mapping**
- `Mapper` class — rescales a processed axis value from any source range to any target range
- `invert` flag — flip the output direction without swapping the target tuple
- `clamp` option (default `True`) — prevents out-of-range output when a stick is not perfectly zeroed
- `center_deadband` — snaps output to the exact target midpoint within a configurable band; useful for ESCs sensitive around neutral
- `Mapper.center` property — returns the exact midpoint of the target range
- `PWM()` preset — maps to microsecond pulse widths (default 1000–2000 µs); supports `one_sided`, `invert`, and `center_deadband`
- `SERVO()` preset — maps to degrees (default -90° to +90°); supports `invert` and `center_deadband`
- `MOTOR()` preset — maps to motor driver byte values (default 0–255); supports `one_sided`, `invert`, and `center_deadband`

---

## [0.2.1] — 2026-04-08

### Added

**Recording and playback**
- The new changes were added to the README file.

---

## [0.2.0] — 2026-04-08

### Added

**Recording & Playback**
- `Gamepad.start_recording()` — begin capturing raw controller input into a `Session`
- `Gamepad.stop_recording()` — end the recording and return the completed `Session`
- `Gamepad.playback(session, speed=1.0, profile=None)` — replay a recorded session through the full callback pipeline without hardware
- `Gamepad.playback_async(session, ...)` — non-blocking playback in a background daemon thread
- `Session` — data model for a complete recording: metadata, duration, and ordered snapshots
- `Snapshot` — immutable, timestamped raw hardware state (axes, buttons, hats); stored before profile mapping, deadzone, and filtering so sessions can be replayed with different settings
- `Session.save(path)` — serialise a session to human-readable, diff-friendly JSON (format version 1)
- `Session.load(path)` — deserialise a session; validates format version and rejects corrupt files with clear error messages
- `recording_playback.py` example — demonstrates the full record → save → load → playback workflow

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
