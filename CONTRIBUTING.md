# Contributing to controlpad

Thank you for taking the time to contribute.

---

## Getting started

```bash
git clone https://github.com/ranaweerasupun/controlpad.git
cd controlpad
pip install -e ".[dev]"
```

Run the tests:

```bash
pytest
```

---

## Adding a controller profile

The easiest way to contribute is adding support for a controller that isn't
covered yet. Here's the process:

1. Connect your controller and run `controlpad detect` to see raw axis indices.
2. Move each stick and press each button to confirm the mapping.
3. Create a new file under `controlpad/profiles/your_controller.py` following
   the pattern in `dualsense.py`.
4. Add it to the registry in `controlpad/profiles/__init__.py`.
5. Add tests in `tests/test_profiles.py`.
6. Open a pull request with the controller name and the OS/driver you tested on.

---

## Code style

This project uses `ruff` for linting. Run before submitting:

```bash
ruff check controlpad tests
```

---

## Reporting bugs

Open an issue and include:

- Your OS and Python version
- Controller make and model
- Output of `controlpad detect`
- A minimal code snippet that reproduces the problem

---

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] New code is covered by tests
- [ ] `ruff` reports no errors
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
