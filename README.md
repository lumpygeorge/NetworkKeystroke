# NetworkKeystroke
This is a Python-based agent that runs on a Windows, macOS, or Linux machine and listens for commands over a TCP network connection (default port 5555). It allows remote control of the machine by simulating keyboard input, mouse actions, and executing shell commands.

The agent runs persistently in the system tray (notification area) when started.

## Features

*   Remote Keyboard Simulation (typing, special keys, hotkeys like `Ctrl+C`, `Ctrl+Alt+Delete`)
*   Remote Mouse Simulation (move cursor, click buttons)
*   Remote Command Execution (run shell commands - ***Use with Extreme Caution!***)
*   Runs minimized in System Tray.

## Running the Agent

You can run the agent either from the Python source code or using the provided pre-built executable.

**Option 1: Running from Source (`agent.py`)**

1.  **Requirements:**
    *   Python 3.x
    *   Install required libraries:
        ```bash
        pip install pyautogui pystray Pillow
        ```
        *(Note: PyAutoGUI might have specific OS dependencies - see its documentation if needed.)*
2.  **Run:** Open a terminal or command prompt, navigate to the directory containing `agent.py`, and run:
    ```bash
    python agent.py
    ```

**Option 2: Running the Executable (`agent.exe`)**

1.  Simply double-click the `agent.exe` file.
2.  Allow it through any firewall prompts if necessary.

   

**Operation:**

*   Once running, the agent listens on **port 5555** on all network interfaces (`0.0.0.0`).
*   A system tray icon will appear. Right-click the icon and select "Exit" to stop the agent.
*   Console warnings about security will appear if run from a terminal.



## Controlling the Agent

1.  **Establish Connection:** Connect to the agent using a TCP client application (like Netcat, Telnet, Python's `socket` module, or integrated tools like Bitfocus Companion's Generic TCP module).
    *   **Target IP/Hostname:** The IP address or network hostname of the machine running the agent.
    *   **Target Port:** `5555` (or the `DEFAULT_PORT` if changed in the source).
2.  **Send Commands:** Send commands as JSON strings. **Each complete JSON command object MUST be terminated by a newline character (`\n`)**. The agent processes commands sequentially as they are received.

## Command Structure and Reference

All commands are JSON objects with a mandatory `"type"` field indicating the action.


---


### Command Type: `keypress`

Simulates keyboard input.

**JSON Syntax:**
```
{
  "type": "keypress",
  "key": "<key_string>"
  [, "delay": <seconds>]
}
```


#### Parameters:

"key" - (String, Required): The key or sequence to simulate.

Examples: "a", "Hello World!", "enter", "tab", "f5", "ctrl+c", "alt+f4", "ctrl+alt+delete", "C:\\Path\\File.txt"

"delay" - (Float, Optional): Sets the interval between characters for typewrite actions and adds a pause after the command. Defaults to 0.01 seconds if omitted.

Use Cases: Typing text, pressing Enter/Tab, triggering application shortcuts.

#### Examples:

Example JSON Commands (each sent followed by \n):

```
{"type": "keypress", "key": "login_username"}\n
```
```
{"type": "keypress", "key": "tab"}\n
```
```
{"type": "keypress", "key": "P@sswOrd!"}\n
```
```
{"type": "keypress", "key": "enter", "delay": 0.1}\n
```
```
{"type": "keypress", "key": "ctrl+s"}\n
```
### Command Type: `mousemove`

Moves the mouse cursor.

JSON Syntax:
```
{
  "type": "mousemove",
  "x": <x_coord>,
  "y": <y_coord>
  [, "duration": <seconds>]
}
```

#### Parameters:

"x" (Integer, Required): Target horizontal screen coordinate (pixels from left).

"y" (Integer, Required): Target vertical screen coordinate (pixels from top).

"duration" (Float, Optional): Time in seconds for the move (0 for instant). Defaults to 0.1.

Use Cases: Positioning the cursor for clicking or interaction.

#### Examples:
Example JSON Commands (each sent followed by \n):

```
{"type": "mousemove", "x": 800, "y": 600}\n
```
```
{"type": "mousemove", "x": 0, "y": 0, "duration": 0.5}\n
```

### Command Type: `mouseclick`

Performs a mouse click.

JSON Syntax:

```
{
  "type": "mouseclick"
  [, "button": "<btn_name>"]
  [, "clicks": <click_count>]
  [, "interval": <seconds>]
  [, "x": <x_coord>]
  [, "y": <y_coord>]
}
```

#### Parameters:

"button" (String, Optional): Button to click: "left", "right", "middle". Defaults to "left".

"clicks" (Integer, Optional): Number of clicks. Defaults to 1.

"interval" (Float, Optional): Pause between clicks if clicks > 1. Defaults to 0.0.

"x" (Integer, Optional): If set (with y), move instantly to this X coordinate before clicking.

"y" (Integer, Optional): If set (with x), move instantly to this Y coordinate before clicking.

Use Cases: Clicking UI elements, selecting items, triggering context menus.

#### Examples
Example JSON Commands (each sent followed by \n):

```
{"type": "mouseclick", "button": "right"}\n
```
```
{"type": "mouseclick", "clicks": 2, "interval": 0.05}\n
```
```
{"type": "mouseclick", "x": 125, "y": 350}\n
```

### Command Type: `runcommand` (SECURITY RISK!)

Executes a command using the system's default shell.

JSON Syntax:

```
{
  "type": "runcommand",
  "command": "<command_string>"
}
```

#### Parameters:

"command" (String, Required): The exact command line string to execute on the agent machine.

Use Cases: Launching applications, simple system tasks. Potentially very dangerous.

#### Examples:
Example JSON Commands (each sent followed by \n):

```
{"type": "runcommand", "command": "notepad.exe"}\n
```
```
{"type": "runcommand", "command": "ipconfig"}\n
```

Security Considerations - VERY IMPORTANT!

Network: The agent listens on ALL network interfaces. Ensure it runs on a trusted, private network. Do NOT expose port 5555 directly to the internet. Use firewalls to restrict access if possible.

Authentication: There is NO authentication. Anyone who can reach the agent can send commands.

runcommand DANGER: The runcommand type allows REMOTE CODE EXECUTION. This is a major security risk. Anyone controlling the agent can potentially take over the machine. DO NOT USE runcommand unless you absolutely understand and accept the risks and operate on a completely secure, isolated network.

Use this software responsibly.
