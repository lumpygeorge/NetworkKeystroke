import socket
import platform # Keep for potential future OS-specific logic
import json
import time
import signal
import sys
import threading
import pyautogui
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import multiprocessing
import select
import subprocess # Needed for runcommand

# --- Configuration ---
DEFAULT_PORT = 5555
DEFAULT_DELAY = 0.01 # Renamed for clarity
MOUSE_MOVE_DURATION = 0.1 # Default duration for smooth mouse moves

# --- Global State ---
shutdown_flag = threading.Event()

# --- Simulation Functions ---

def simulate_keypress(key, delay):
    """Simulates keyboard actions based on the key string."""
    if shutdown_flag.is_set(): return
    try:
        pyautogui.PAUSE = 0.0 # Ensure no global PyAutoGUI pause

        # 1. Multi-key hotkeys (e.g., ctrl+alt+delete)
        if key.count('+') > 1:
            hotkey_parts = [k.strip().lower() for k in key.split('+')]
            print(f"Executing hotkey: {hotkey_parts}")
            pyautogui.hotkey(*hotkey_parts)

        # 2. Single modifier + key (e.g., ctrl+c)
        elif "+" in key:
            parts = key.split("+", 1)
            if len(parts) == 2:
                mods, k = parts[0].strip().lower(), parts[1].strip().lower()
                print(f"Applying modifier: {mods}, Key: {k}")
                with pyautogui.hold(mods):
                    pyautogui.press(k)
            else: # Malformed, type literally
                print(f"Warning: Malformed modifier key '{key}', typing literally.")
                pyautogui.typewrite(key, interval=delay)

        # 3. Special single keys (e.g., enter, tab, f1)
        elif key.lower() in pyautogui.KEYBOARD_KEYS:
            print(f"Pressing special key: {key.lower()}")
            pyautogui.press(key.lower())

        # 4. Longer strings to type
        elif len(key) > 1:
            print(f"Typing string (truncated): {key[:30]}...")
            pyautogui.typewrite(key, interval=delay)

        # 5. Single regular characters (handles uppercase via typewrite)
        elif key:
            print(f"Typing single char: {key}")
            pyautogui.typewrite(key) # Handles shift for single uppercase chars

        time.sleep(delay) # Pause after action

    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Error simulating keypress '{key}': {e}")

def simulate_mousemove(x, y, duration):
    """Moves the mouse cursor to the specified coordinates."""
    if shutdown_flag.is_set(): return
    try:
        print(f"Moving mouse to ({x}, {y}) over {duration}s")
        pyautogui.moveTo(x, y, duration=duration)
    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Error moving mouse: {e}")

def simulate_mouseclick(button='left', clicks=1, interval=0.0, x=None, y=None):
    """Performs a mouse click."""
    if shutdown_flag.is_set(): return
    try:
        # Validate button
        valid_buttons = ['left', 'right', 'middle']
        if button.lower() not in valid_buttons:
            print(f"Error: Invalid mouse button '{button}'. Use one of {valid_buttons}.")
            return

        # If coordinates are provided, move first (instantly)
        if x is not None and y is not None:
             print(f"Moving mouse instantly to ({x}, {y}) before click")
             pyautogui.moveTo(x, y, duration=0) # Instant move

        print(f"Clicking mouse: button={button}, clicks={clicks}, interval={interval}")
        pyautogui.click(clicks=clicks, interval=interval, button=button.lower())

    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Error simulating mouse click: {e}")

def simulate_runcommand(command_str):
    """
    Executes a shell command. SECURITY RISK!
    Uses Popen for non-blocking execution.
    """
    if shutdown_flag.is_set(): return
    # --- !!! SECURITY WARNING !!! ---
    # Executing arbitrary commands received over the network is highly insecure.
    # Use this feature with extreme caution and only in trusted environments.
    # Consider adding validation or restricting allowed commands.
    # --- !!! END SECURITY WARNING !!! ---
    try:
        print(f"Executing command: {command_str}")
        # Use Popen to run the command in the background without blocking the agent
        process = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # We don't wait for the command to finish here (process.wait())
        # You could optionally read stdout/stderr if needed, but that adds complexity
        print(f"Command '{command_str}' initiated with PID: {process.pid}")
        # Note: Error checking for the command *itself* (e.g., command not found)
        # would require checking process.returncode after process.wait() or using communicate().
        # For now, we just launch it.
    except FileNotFoundError:
         print(f"Error: Command not found: {command_str}")
    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"Error executing command '{command_str}': {e}")


# --- Network Handling ---
def handle_client(conn, addr):
    """Handles incoming commands from a controller."""
    print(f"Handling connection from {addr}")
    buffer = "" # Buffer for potentially fragmented messages
    try:
        while not shutdown_flag.is_set():
            ready_to_read, _, _ = select.select([conn], [], [], 0.5)
            if not ready_to_read:
                continue

            data = conn.recv(1024)
            if not data:
                print(f"Connection closed by controller {addr}.")
                break

            buffer += data.decode('utf-8')

            # Process complete JSON objects separated by newline (or other delimiter if protocol changes)
            while '\n' in buffer: # Assuming newline separates commands sent by controller
                command_json, buffer = buffer.split('\n', 1)
                command_json = command_json.strip()
                if not command_json: continue

                try:
                    command = json.loads(command_json)
                    cmd_type = command.get("type")
                    print(f"Processing command: {cmd_type}") # Debug

                    if cmd_type == "keypress":
                        simulate_keypress(
                            command.get("key"),
                            command.get("delay", DEFAULT_DELAY)
                            # Modifiers are handled inside simulate_keypress via '+'
                        )
                    elif cmd_type == "mousemove":
                         x = command.get("x")
                         y = command.get("y")
                         if x is not None and y is not None:
                              try:
                                   simulate_mousemove(int(x), int(y), command.get("duration", MOUSE_MOVE_DURATION))
                              except (ValueError, TypeError):
                                   print("Error: Invalid x/y coordinates for mousemove.")
                         else:
                              print("Error: Missing 'x' or 'y' for mousemove.")

                    elif cmd_type == "mouseclick":
                         try:
                              # Get args, providing defaults using .get
                              simulate_mouseclick(
                                   button=command.get("button", 'left'),
                                   clicks=int(command.get("clicks", 1)),
                                   interval=float(command.get("interval", 0.0)),
                                   x=int(command["x"]) if "x" in command else None, # Handle optional coords
                                   y=int(command["y"]) if "y" in command else None
                              )
                         except (ValueError, TypeError):
                              print("Error: Invalid parameter type for mouseclick.")

                    elif cmd_type == "runcommand":
                         cmd_str = command.get("command")
                         if cmd_str:
                              simulate_runcommand(cmd_str)
                         else:
                              print("Error: Missing 'command' string for runcommand.")

                    else:
                        print(f"Unknown command type: {cmd_type}")

                except json.JSONDecodeError as json_err:
                    print(f"Invalid JSON received from {addr}: {json_err}")
                    print(f"Data fragment: {command_json}") # Show the problematic fragment
                    # Decide whether to clear buffer or break connection on bad JSON
                    buffer = "" # Clear buffer after error
                    # break # Or break connection
                except ConnectionResetError:
                    print(f"Connection with {addr} reset.")
                    raise # Re-raise to break outer loop
                except Exception as e:
                    # Catch processing errors for a single command
                    if not shutdown_flag.is_set():
                         print(f"Error processing command ({command_json}): {e}")
                    # Continue to next command if possible

    except ConnectionResetError: # Catch reset if it happens during recv/select
         print(f"Connection with {addr} reset (outer loop).")
    except Exception as e:
         if not shutdown_flag.is_set():
              print(f"Error in handle_client for {addr}: {e}")
    finally:
        print(f"Closing handling for connection {addr}")
        try:
            # Attempt graceful shutdown of the socket directions
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            # Socket might already be closed
            pass
        conn.close()


# --- System Tray ---
def create_default_icon_image():
    """Creates a simple default icon."""
    width, height = 64, 64
    color1, color2 = (0,0,0), (255,255,255) # Black and White
    image = Image.new('RGB', (width, height), color1)
    d = ImageDraw.Draw(image)
    # Simple design (e.g., white square with black inner square)
    d.rectangle((width // 8, height // 8, width * 7 // 8, height * 7 // 8), fill=color2)
    d.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color1)
    return image

def exit_action(icon, item):
    """Callback for the tray icon's Exit menu item."""
    print("Exit action called from tray.")
    shutdown_flag.set()
    icon.stop()
    # Terminate server process if using multiprocessing
    if 'server_process' in globals() and isinstance(server_process, multiprocessing.Process) and server_process.is_alive():
        print("Terminating server process...")
        server_process.terminate()
        server_process.join(timeout=1)

# --- Server ---
def start_server():
    """Starts the main TCP server to listen for controller connections."""
    host = '0.0.0.0'
    port = DEFAULT_PORT
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Agent server component listening on {host}:{port}")
        server_socket.settimeout(1.0) # For periodic shutdown check

        while not shutdown_flag.is_set():
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                client_thread.start()
            except socket.timeout:
                continue
            except OSError: # Handle socket closed during shutdown
                 if shutdown_flag.is_set(): break
                 else: raise # Reraise if not during shutdown
            except Exception as e:
                 if not shutdown_flag.is_set(): print(f"Error accepting connection: {e}")
                 time.sleep(1)

    except Exception as e:
        if not shutdown_flag.is_set(): print(f"Error setting up server socket: {e}")
    finally:
        print("Agent server component shutting down.")
        server_socket.close()

# --- Main Execution ---
def main():
    """Main function: sets up signals, icon, and starts server."""
    global server_process # Needed if using multiprocessing

    # --- Signal Handler for Main Process ---
    def main_process_shutdown(sig, frame):
        print(f'Main process received signal {sig}, initiating shutdown.')
        shutdown_flag.set() # Signal components to stop

    signal.signal(signal.SIGINT, main_process_shutdown)
    signal.signal(signal.SIGTERM, main_process_shutdown)

    # --- Icon Setup ---
    try:
        image = Image.open("icon.png")
        print("Loaded icon from icon.png")
    except FileNotFoundError:
        print("icon.png not found, creating default icon.")
        image = create_default_icon_image()
    except Exception as e:
        print(f"Error loading icon: {e}, creating default icon.")
        image = create_default_icon_image()

    menu = (item('Exit', exit_action),)
    icon = pystray.Icon("NetworkAgent", image, "Network Agent", menu) # Shorter name

    print("Starting server component...")
    # --- Choose Thread or Process ---
    # Defaulting to Thread for simplicity unless multiprocessing is explicitly needed
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    # server_process = multiprocessing.Process(target=start_server, daemon=True)
    # server_process.start()

    print("Starting system tray icon. Use Exit from tray or send signal (Ctrl+C) to stop.")
    # --- SECURITY WARNING ---
    print("!!! WARNING: Agent listening on all interfaces.")
    print("!!! Ensure network is secure or implement authentication.")
    print("!!! 'runcommand' type is enabled - EXTREME CAUTION ADVISED.")
    # --- END WARNING ---
    try:
        icon.run() # Blocks main thread
    finally:
        print("System tray icon stopped.")
        if not shutdown_flag.is_set(): shutdown_flag.set() # Ensure flag is set
        # Wait for server thread/process
        if 'server_thread' in locals() and server_thread.is_alive():
            server_thread.join(timeout=2)
        # if 'server_process' in locals() and server_process.is_alive():
        #    server_process.join(timeout=2)
        print("Agent main process exiting.")

# --- Entry Point ---
if __name__ == "__main__":
    # freeze_support() for PyInstaller multiprocessing compatibility
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        multiprocessing.freeze_support()
        print("Multiprocessing freeze support enabled.")

    # Check if PyAutoGUI is available before starting fully
    try:
        pyautogui.size() # A simple check to see if the library works
    except Exception as e:
        print(f"CRITICAL ERROR: PyAutoGUI failed to initialize: {e}")
        print("The agent cannot function without PyAutoGUI.")
        sys.exit(1)

    main()