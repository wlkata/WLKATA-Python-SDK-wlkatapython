"""Utility helpers for WLKATA robot classes."""

import functools
import warnings

_DEPRECATED_KEYS = {"mooe": "mode"}

_MOTION_CODES = {0: "G00", 1: "G01", 2: "G05"}
_POSITION_CODES = {0: "G90", 1: "G91"}
_GRIPPER_PWM = {0: 0, 1: 40, 2: 60}
_PUMP_PWM = {0: 0, 1: 1000, 2: 500}

_GPIO_PIN_INDEX = {"A0": 0, "A1": 1, "D0": 2, "D1": 3}

_STATUS_KEYS = (
    "state",
    "angle_A", "angle_B", "angle_C", "angle_D",
    "angle_X", "angle_Y", "angle_Z",
    "coordinate_X", "coordinate_Y", "coordinate_Z",
    "coordinate_RX", "coordinate_RY", "coordinate_RZ",
    "pump", "valve", "mode",
)

_ANGLE_MAP = {1: "angle_X", 2: "angle_Y", 3: "angle_Z",
              4: "angle_A", 5: "angle_B", 6: "angle_C", 7: "angle_D"}
_COORDINATE_MAP = {1: "coordinate_X", 2: "coordinate_Y", 3: "coordinate_Z",
                   4: "coordinate_RX", 5: "coordinate_RY", 6: "coordinate_RZ"}

_4AXIS_ANGLE_MAP = {k: v for k, v in _ANGLE_MAP.items() if k in (1, 2, 3, 4, 7)}
_4AXIS_COORDINATE_MAP = {k: v for k, v in _COORDINATE_MAP.items() if k in (1, 2, 3, 4)}

_ERROR_MESSAGES = {
    1: "No reply - 'ok'",
    2: "parameter error",
    3: "regular expression error",
    4: "File run error",
}


class _DeprecatedKeyDict(dict):
    """A dict subclass that supports deprecated key aliases with warnings."""

    def __getitem__(self, key):
        new_key = _DEPRECATED_KEYS.get(key)
        if new_key is not None:
            warnings.warn(
                f"Key '{key}' is deprecated, use '{new_key}' instead",
                DeprecationWarning, stacklevel=2,
            )
            return super().__getitem__(new_key)
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        new_key = _DEPRECATED_KEYS.get(key)
        if new_key is not None:
            warnings.warn(
                f"Key '{key}' is deprecated, use '{new_key}' instead",
                DeprecationWarning, stacklevel=2,
            )
            super().__setitem__(new_key, value)
        else:
            super().__setitem__(key, value)

    def __contains__(self, key):
        new_key = _DEPRECATED_KEYS.get(key)
        if new_key is not None:
            return super().__contains__(new_key)
        return super().__contains__(key)


def build_gpio_cmd(register, pin, num):
    """Build a GPIO command string for a given register, pin, and value.

    Args:
        register (str): Register number (e.g. "o130", "o131").
        pin (str): Pin name after capitalize() (e.g. "A0", "D1").
        num: Value to set.

    Returns:
        str: The command string, or None if pin is invalid.
    """
    idx = _GPIO_PIN_INDEX.get(pin)
    if idx is None:
        return None
    parts = [""] * 4
    parts[idx] = str(num)
    return f"{register}={','.join(parts)}"


def parse_gpio_response(pin, match):
    """Extract the value for a specific pin from a regex match of 4 groups.

    Args:
        pin (str): Pin name after capitalize() (e.g. "A0", "D1").
        match: A regex match object with 4 groups.

    Returns:
        str or None: The matched group value, or None if pin is invalid.
    """
    idx = _GPIO_PIN_INDEX.get(pin)
    if idx is None:
        return None
    return match.group(idx + 1)


def deprecated_alias(new_name, version):
    """Create a deprecated method that delegates to the renamed version.

    Args:
        new_name (str): The new method name to delegate to.

    Returns:
        A wrapper function that emits a DeprecationWarning and calls the new method.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            warnings.warn(
                f"{func.__name__}() is deprecated and will be removed in v{version}, "
                f"use {new_name}() instead",
                DeprecationWarning, stacklevel=2,
            )
            return getattr(self, new_name)(*args, **kwargs)
        return wrapper
    return decorator
