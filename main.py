import json
import logging
import os
import platform
import sys
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame


def enable_ansi_colors():
    if os.name != "nt":
        return

    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE

    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)


# --------------------------------------------------
# PROJECT SETTINGS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
MAP_FILE = ROOT / "maps" / "map.json"

DEADZONE = 0.08
POLL_DELAY_MS = 8
AXIS_LOG_THRESHOLD = 0.15
TRIGGER_LOG_THRESHOLD = 0.05

DEFAULT_RIGHT_STICK_SENSITIVITY = 1.5
MIN_RIGHT_STICK_SENSITIVITY = 0.1
MAX_RIGHT_STICK_SENSITIVITY = 5.0

enable_ansi_colors()

# --------------------------------------------------
# COLORED LOGGING (ANSI; Windows Terminal/PowerShell)
# --------------------------------------------------

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[32m",      # Green
        logging.ERROR: "\033[31m",     # Red
        logging.WARNING: "\033[33m",   # Yellow
        logging.DEBUG: "\033[36m",     # Cyan
        logging.CRITICAL: "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        if not color:
            return message
        return f"{color}{message}{self.RESET}"


_handler = logging.StreamHandler()
_handler.setFormatter(ColorFormatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
))
_root_logger = logging.getLogger()
_root_logger.handlers.clear()
_root_logger.addHandler(_handler)
_root_logger.setLevel(logging.INFO)

log = logging.getLogger("JioController")


# --------------------------------------------------
# LOAD AND VALIDATE MAP
# --------------------------------------------------

def load_map():
    if not MAP_FILE.is_file():
        raise FileNotFoundError(f"Map not found: {MAP_FILE}")

    try:
        with MAP_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {MAP_FILE}, "
            f"line {error.lineno}, column {error.colno}"
        ) from error

    controls = data.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("Map must contain a 'controls' object.")

    required = [
        "A Button", "B Button", "X Button", "Y Button",
        "Left Bumper (LB)", "Right Bumper (RB)",
        "Start", "Back / Select",
        "Left Stick Click (L3)", "Right Stick Click (R3)",
        "Left Trigger (LT)", "Right Trigger (RT)",
        "D-Pad Up", "D-Pad Down",
        "D-Pad Left", "D-Pad Right",
        "Left Stick Left", "Left Stick Right",
        "Left Stick Up", "Left Stick Down",
        "Right Stick Left", "Right Stick Right",
        "Right Stick Up", "Right Stick Down",
    ]

    missing = [name for name in required if name not in controls]
    if missing:
        raise ValueError(f"Map is missing controls: {', '.join(missing)}")

    for name, info in controls.items():
        if (
            not isinstance(info, dict)
            or info.get("type") not in ("button", "axis", "hat")
            or not isinstance(info.get("index"), int)
            or info["index"] < 0
        ):
            raise ValueError(f"Invalid mapping entry: {name}")

        if info["type"] == "hat" and not isinstance(info.get("value"), list):
            raise ValueError(f"Invalid hat direction in mapping: {name}")

    log.info("Loaded map: %s", MAP_FILE)
    log.info("Controller name: %s", data.get("controller_name", "Unknown"))
    log.info("Mapped controls: %d", len(controls))
    return data


# --------------------------------------------------
# SENSITIVITY
# --------------------------------------------------

def ask_right_stick_sensitivity():
    """Ask for right-stick sensitivity at launch; Enter selects the default."""
    while True:
        raw = input(
            f"Right-stick look sensitivity "
            f"[{MIN_RIGHT_STICK_SENSITIVITY:.1f}x-"
            f"{MAX_RIGHT_STICK_SENSITIVITY:.1f}x, "
            f"Enter = {DEFAULT_RIGHT_STICK_SENSITIVITY:.1f}x]: "
        ).strip()

        if not raw:
            value = DEFAULT_RIGHT_STICK_SENSITIVITY
            break

        try:
            value = float(raw)
        except ValueError:
            log.warning("Enter a number such as 1.0, 1.5, or 2.0.")
            continue

        if not MIN_RIGHT_STICK_SENSITIVITY <= value <= MAX_RIGHT_STICK_SENSITIVITY:
            log.warning(
                "Sensitivity must be between %.1fx and %.1fx.",
                MIN_RIGHT_STICK_SENSITIVITY,
                MAX_RIGHT_STICK_SENSITIVITY,
            )
            continue
        break

    log.info("Right-stick look sensitivity: %.2fx", value)
    return value


def apply_sensitivity(value, sensitivity):
    """Scale a stick axis and clamp it to the valid virtual-stick range."""
    return max(-1.0, min(1.0, float(value) * sensitivity))


# --------------------------------------------------
# PHYSICAL CONTROLLER
# --------------------------------------------------

def connect_controller():
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    if count == 0:
        raise RuntimeError(
            "No physical controller found. Connect your Jio controller "
            "and run the program again."
        )

    for index in range(count):
        device = pygame.joystick.Joystick(index)
        log.info(
            "Device %d: %s | buttons=%d axes=%d hats=%d",
            index,
            device.get_name(),
            device.get_numbuttons(),
            device.get_numaxes(),
            device.get_numhats(),
        )

    controller = pygame.joystick.Joystick(0)
    controller.init()
    log.info("Using physical controller: %s", controller.get_name())
    return controller


def read_control(controller, info):
    kind = info["type"]
    index = info["index"]

    if kind == "button":
        if index < controller.get_numbuttons():
            return controller.get_button(index)

    elif kind == "axis":
        if index < controller.get_numaxes():
            return controller.get_axis(index)

    elif kind == "hat":
        if index < controller.get_numhats():
            return controller.get_hat(index)

    raise RuntimeError(
        f"Mapped {kind} index {index} is unavailable on this controller."
    )


# --------------------------------------------------
# TRANSLATION HELPERS
# --------------------------------------------------

def apply_deadzone(value):
    """Remove stick drift while preserving the remaining range."""
    value = max(-1.0, min(1.0, float(value)))

    if abs(value) <= DEADZONE:
        return 0.0

    scaled = (abs(value) - DEADZONE) / (1.0 - DEADZONE)
    return (1.0 if value > 0 else -1.0) * scaled


def normalize_trigger(raw_value, info):
    """
    Convert the physical trigger axis to Xbox trigger range 0.0..1.0.
    The recorded pressed sample determines which direction means pressed.
    """
    rest = float(info.get("rest_value", -1.0))
    sample = float(info.get("value_when_pressed", 1.0))

    if abs(sample - rest) < 0.01:
        raise ValueError(
            "Trigger pressed sample is too close to its rest value."
        )

    if sample > rest:
        result = (raw_value - rest) / (1.0 - rest)
    else:
        result = (rest - raw_value) / (rest + 1.0)

    return max(0.0, min(1.0, result))


def read_stick(controller, controls, prefix):
    """
    Pygame's Y axis is negative when pushed up.
    Convert it to the Xbox stick convention: positive Y is up.
    """
    x_info = controls[f"{prefix} Stick Right"]
    y_info = controls[f"{prefix} Stick Down"]

    x = float(read_control(controller, x_info))
    y = float(read_control(controller, y_info))

    return apply_deadzone(x), apply_deadzone(-y)


def dpad_pressed(controller, controls, name):
    info = controls[name]
    actual = read_control(controller, info)
    expected = tuple(info["value"])

    # Cardinal directions also work when the hat is diagonal.
    return (
        expected != (0, 0)
        and (expected[0] == 0 or actual[0] == expected[0])
        and (expected[1] == 0 or actual[1] == expected[1])
    )


# --------------------------------------------------
# VIRTUAL XBOX 360 CONTROLLER
# --------------------------------------------------

def create_virtual_controller():
    try:
        import vgamepad as vg
    except ImportError as error:
        raise RuntimeError(
            "Missing vgamepad. Install it with: "
            "python -m pip install vgamepad"
        ) from error

    log.info("Operating system: %s", platform.system())
    log.info("Creating virtual Xbox 360 controller...")

    try:
        gamepad = vg.VX360Gamepad()
    except Exception as error:
        raise RuntimeError(
            "Could not create the virtual controller. Check that the "
            "required Windows driver or Linux uinput support is installed "
            "and accessible."
        ) from error

    gamepad.reset()
    gamepad.update()

    log.info("Virtual Xbox 360 controller created.")
    return vg, gamepad


# --------------------------------------------------
# MAIN INPUT LOOP
# --------------------------------------------------

def main():
    virtual = None

    try:
        mapping = load_map()
        controls = mapping["controls"]

        sensitivity = ask_right_stick_sensitivity()
        controller = connect_controller()
        vg, virtual = create_virtual_controller()

        # Physical control name -> virtual Xbox 360 button.
        button_bindings = {
            "A Button": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            "B Button": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            "X Button": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            "Y Button": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            "Left Bumper (LB)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            "Right Bumper (RB)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "Start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            "Back / Select": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            "Left Stick Click (L3)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            "Right Stick Click (R3)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            "D-Pad Up": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            "D-Pad Down": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            "D-Pad Left": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            "D-Pad Right": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        }

        previous_buttons = set()
        previous_axes = {}
        previous_triggers = {}

        log.info("=" * 55)
        log.info("JIO -> VIRTUAL XBOX 360 BRIDGE RUNNING")
        log.info("Right-stick sensitivity: %.2fx", sensitivity)
        log.info("Press Ctrl+C to stop.")
        log.info("=" * 55)

        while True:
            pygame.event.pump()

            # Collect physical button and D-pad states.
            active_buttons = set()

            for name, xbox_button in button_bindings.items():
                if name.startswith("D-Pad "):
                    pressed = dpad_pressed(controller, controls, name)
                else:
                    pressed = bool(read_control(controller, controls[name]))

                if pressed:
                    active_buttons.add(xbox_button)

                # Log physical button edges.
                if pressed and xbox_button not in previous_buttons:
                    log.info("PRESS   | %s", name)
                elif not pressed and xbox_button in previous_buttons:
                    log.info("RELEASE | %s", name)

            # Send only button state changes to the virtual device.
            for button in active_buttons - previous_buttons:
                virtual.press_button(button=button)

            for button in previous_buttons - active_buttons:
                virtual.release_button(button=button)

            previous_buttons = active_buttons

            # Read and translate both sticks.
            lx, ly = read_stick(controller, controls, "Left")
            raw_rx, raw_ry = read_stick(controller, controls, "Right")
            rx = apply_sensitivity(raw_rx, sensitivity)
            ry = apply_sensitivity(raw_ry, sensitivity)

            axes = {
                "Left Stick X": lx,
                "Left Stick Y": ly,
                "Right Stick X": rx,
                "Right Stick Y": ry,
            }

            for name, value in axes.items():
                old = previous_axes.get(name)
                if old is None or abs(value - old) >= AXIS_LOG_THRESHOLD:
                    if abs(value) > 0.0 or (old is not None and old != 0.0):
                        log.info("STICK   | %s = %.2f", name, value)
                    previous_axes[name] = value

            virtual.left_joystick_float(
                x_value_float=lx, y_value_float=ly
            )
            virtual.right_joystick_float(
                x_value_float=rx, y_value_float=ry
            )

            # Normalize the trigger axes into 0.0..1.0.
            for name, setter in (
                ("Left Trigger (LT)", virtual.left_trigger_float),
                ("Right Trigger (RT)", virtual.right_trigger_float),
            ):
                raw = float(read_control(controller, controls[name]))
                value = normalize_trigger(raw, controls[name])
                old = previous_triggers.get(name)

                if old is None or abs(value - old) >= TRIGGER_LOG_THRESHOLD:
                    if value > 0.0 or (old is not None and old > 0.0):
                        log.info("TRIGGER | %s = %.2f", name, value)
                    previous_triggers[name] = value

                setter(value_float=value)

            # Publish the complete virtual controller state.
            virtual.update()
            pygame.time.wait(POLL_DELAY_MS)

    except KeyboardInterrupt:
        log.info("Stopping controller bridge...")

    except (OSError, ValueError, RuntimeError, KeyError) as error:
        log.error("%s", error)
        return 1

    finally:
        if virtual is not None:
            try:
                virtual.reset()
                virtual.update()
                log.info("Virtual controller reset.")
            except Exception as error:
                log.warning("Could not reset virtual controller: %s", error)

        pygame.quit()
        log.info("Exited.")

    return 0


if __name__ == "__main__":
    sys.exit(main())