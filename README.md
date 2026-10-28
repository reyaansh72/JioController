# JioController 🎮

**Use your Jio Bluetooth controller as a virtual Xbox 360 controller.**

JioController is a Python-based controller bridge that reads input from a physical Jio Bluetooth controller and translates it into input for a virtual Xbox 360 gamepad.

This allows compatible games and applications to receive controller input through a virtual Xbox 360 controller.

## ✨ Features

- 🎮 **Virtual Xbox 360 controller** — translates physical controller input into virtual gamepad input.
- 🕹️ **Analog stick support** — maps both physical sticks to the virtual controller.
- 🎯 **Adjustable look sensitivity** — configure right-stick sensitivity every time you launch the program.
- 🔘 **Button mapping** — supports face buttons, bumpers, stick clicks, Start, Back/Select, and the D-pad.
- 🏹 **Trigger normalization** — converts physical trigger input to the virtual Xbox trigger range.
- 🛡️ **Deadzone handling** — helps reduce unwanted analog stick drift.
- 🌈 **Colored logging** — INFO messages are green, warnings are yellow, and errors are red in compatible terminals.
- 🗺️ **JSON-based configuration** — controller mappings are stored in a separate file.

## 📁 Project Structure

```text
JioController/
├── main.py
├── README.md
└── maps/
    └── map.json
```

## ⚙️ Requirements

- Python 3
- A Jio Bluetooth controller, paired and connected to your computer
- `pygame`
- `vgamepad`
- A supported virtual gamepad backend and its required driver or system support

On Windows, `vgamepad` generally uses the ViGEmBus virtual gamepad driver.

## 🚀 Installation

### 1. Install the Python dependencies

Open a terminal in the project directory and run:

```powershell
python -m pip install pygame vgamepad
```

### 2. Set up the virtual controller

On Windows, install the required ViGEmBus driver if it is not already installed.

### 3. Connect your Jio controller

Pair your Jio Bluetooth controller with your computer and ensure it is connected before launching the program.

### 4. Launch JioController

Run:

```powershell
python main.py
```

The program will load the controller mapping, ask for your right-stick sensitivity, detect the physical controller, and create the virtual Xbox 360 controller.

## 🎯 Right-Stick Look Sensitivity

JioController asks you to configure right-stick sensitivity at startup:

```text
Right-stick look sensitivity [0.1x-5.0x, Enter = 1.5x]:
```

Enter a value between `0.1` and `5.0`, or press Enter to use the default of `1.5x`.

| Sensitivity | Effect |
|---:|---|
| `0.5x` | Slower camera movement |
| `1.0x` | Original stick response |
| `1.5x` | Increased sensitivity |
| `2.0x` | Double the input strength |
| `3.0x` | Much faster camera movement |
| `5.0x` | Maximum input amplification |

Sensitivity affects **only the right stick**. It does not amplify the left stick, buttons, D-pad, or triggers.

Higher sensitivity can make the virtual stick reach its maximum value sooner. Choose a setting that feels comfortable for your game.

The selected sensitivity applies for the current run. You can choose a different value the next time you launch JioController.

## 🎮 Controller Mapping

The default mapping in `maps/map.json` is designed specifically for the **Jio Bluetooth controller**.

For normal users, the default mapping should be left unchanged.

### Default controls

The mapping covers:

- A, B, X, and Y buttons
- Left and right bumpers
- Left and right triggers
- Start and Back/Select
- Left and right stick clicks
- D-pad directions
- Left-stick movement directions
- Right-stick movement and look directions

### Using another controller

**Advanced users only:** The mapping can be modified to support another controller by adjusting the button, axis, and hat indices to match that device.

This requires understanding how the controller reports its inputs and how the JSON mapping is structured. Incorrect mappings can cause controls to behave incorrectly or become unavailable.

**For normal users:** If you're using the intended Jio Bluetooth controller, keep the default mapping unchanged.

Mapping file:

```text
maps/map.json
```

## 🌈 Colored Logging

JioController provides timestamped logs to show startup information, controller activity, and errors.

Example:

```text
13:00:28 | INFO    | Virtual Xbox 360 controller created.
13:00:28 | INFO    | JIO -> VIRTUAL XBOX 360 BRIDGE RUNNING
13:00:28 | INFO    | Right-stick sensitivity: 1.50x
```

In compatible terminals, log levels use these colors:

- 🟢 **INFO** — green
- 🟡 **WARNING** — yellow
- 🔴 **ERROR** — red
- 🔵 **DEBUG** — cyan

On Windows, ANSI color support must be enabled for the colors to display correctly. Windows Terminal and compatible PowerShell sessions are recommended.

## 🛑 Stopping JioController

Press `Ctrl+C` in the terminal to stop the program.

JioController attempts to reset the virtual controller before exiting.

## 🔧 Troubleshooting

### No physical controller found

- Ensure the Jio controller is paired and connected.
- Wait for Bluetooth to finish connecting before launching the program.
- Run `python main.py` again if the controller was not detected on the first attempt.

### Virtual Xbox 360 controller creation fails

- Check that the required virtual gamepad driver is installed.
- On Windows, verify the ViGEmBus installation.
- Read the error message printed in the terminal.

### Camera movement is too slow

Increase the right-stick sensitivity at startup. Try `2.0x` or `3.0x`.

### Camera movement is too fast

Choose a lower sensitivity, such as `0.7x` or `1.0x`.

### Logs display ANSI codes instead of colors

Use a terminal that supports ANSI escape sequences and ensure Windows ANSI support is enabled.

### Controller buttons behave incorrectly

If you're using the Jio controller, restore the original `maps/map.json` if you modified it. If you're adapting JioController to another controller, check that the mapped indices match the device's actual inputs.

## ⚠️ Notes

- JioController translates controller input; it does not modify games themselves.
- Compatibility depends on whether the game or application supports input from the virtual controller.
- The physical controller's device name may differ depending on the operating system or input library.
- The default mapping is intended for the Jio Bluetooth controller.
- Support for other controllers requires manual mapping changes by advanced users.

## 📜 License

No license has been specified yet.

If you plan to publish or distribute this project, choose a license and add a `LICENSE` file. Until then, the repository does not declare a specific open-source license.
