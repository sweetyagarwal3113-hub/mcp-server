import subprocess
import time

try:
    import pyautogui
except Exception:
    pyautogui = None


def _ensure_paint_running():
    """Connect to an existing MS Paint instance or launch a new one.
    Returns the pywinauto Application and Window objects.
    """
    if pyautogui is None:
        return None, None, "MS Paint and PyAutoGUI GUI automation is only supported in desktop Windows environments."
    try:
        from pywinauto.application import Application
    except ImportError:
        return None, None, "Please install pywinauto first by running: pip install pywinauto"

    try:
        app = Application(backend="uia").connect(title_re=".*Paint")
        window = app.window(title_re=".*Paint")
    except Exception:
        # No running instance – start Paint
        subprocess.Popen("mspaint.exe")
        time.sleep(2)  # wait for Paint to appear
        app = Application(backend="uia").connect(title_re=".*Paint")
        window = app.window(title_re=".*Paint")
    # Bring to foreground and maximize
    try:
        window.maximize()
    except Exception:
        pass
    window.set_focus()
    time.sleep(1)
    return app, window, None


def draw_shape_logic(shape: str) -> str:
    """Draw the specified shape (rectangle, oval, smiley, etc.) in MS Paint.
    The function opens Paint if needed, selects the shape tool, draws the shape on the canvas,
    and deselects it so that the Fill tool can be used afterwards.
    """
    app, window, err = _ensure_paint_running()
    if err:
        return err
    # Normalise shape name and map to UI title
    shape = shape.lower()
    if shape == "rectangle":
        shape_title = "Rectangle"
    elif shape == "oval":
        shape_title = "Oval"
    elif shape == "smiley":
        shape_title = "Five-point star"
    else:
        shape_title = shape.capitalize()
    # Click the shape button (ListItem on newer Windows, Button on older versions)
    try:
        window.child_window(title=shape_title, control_type="ListItem").click_input()
    except Exception:
        try:
            window.child_window(title=shape_title, control_type="Button").click_input()
        except Exception:
            return f"Shape '{shape_title}' could not be found in MS Paint's UI."
    # Canvas coordinates – centre of the drawing area (adjust if needed)
    canvas_x = 974
    canvas_y = 533
    # Move to canvas and ensure Paint has focus
    pyautogui.moveTo(canvas_x, canvas_y)
    pyautogui.click()
    time.sleep(0.5)
    # Draw the shape by dragging a rectangle (size 200x200)
    pyautogui.mouseDown(button='left')
    pyautogui.moveTo(canvas_x + 200, canvas_y + 200, duration=1.0)
    pyautogui.mouseUp(button='left')
    time.sleep(0.5)
    # Click outside to commit the shape and then deselect it (Esc)
    pyautogui.moveTo(canvas_x - 50, canvas_y - 50)
    pyautogui.click()
    pyautogui.press('esc')
    time.sleep(0.2)
    return f"Successfully drew a {shape}!"


def fill_color_logic(color: str) -> str:
    """Fill the most recently drawn shape with the specified colour.
    Steps:
    1. Select the colour from the colour palette.
    2. Ensure no shape is selected (Esc).
    3. Activate the Fill bucket tool.
    4. Click inside the shape.
    """
    app, window, err = _ensure_paint_running()
    if err:
        return err
    # Choose colour first
    color_title = color.capitalize()
    try:
        window.child_window(title=color_title, control_type="ListItem").click_input()
    except Exception:
        try:
            window.child_window(title=color_title, control_type="Button").click_input()
        except Exception:
            return f"Could not find colour '{color_title}' in MS Paint's UI."
    time.sleep(0.2)
    # Deselect any lingering selection so the Fill tool activates correctly
    pyautogui.press('esc')
    time.sleep(0.2)
    # Ensure Paint has active focus before sending hotkey
    window.set_focus()
    time.sleep(0.2)
    # Activate Fill bucket tool
    try:
        if window.child_window(title="Fill (B)", control_type="Button").exists(timeout=0.5):
            # In newest Windows 11 Paint, hotkey 'B' selects the bucket.
            pyautogui.press('b')
        elif window.child_window(title="Fill with color", control_type="Button").exists(timeout=0.5):
            window.child_window(title="Fill with color", control_type="Button").click_input()
        else:
            window.child_window(title="Fill", control_type="Button").click_input()
    except Exception as e:
        return f"Could not find Fill tool: {e}"
    
    time.sleep(0.5)
    
    canvas_x = 974
    canvas_y = 533
    
    # Ensure Paint window is focused before canvas interaction
    window.set_focus()
    time.sleep(0.2)
    
    # Move inside the drawn shape
    pyautogui.moveTo(canvas_x + 100, canvas_y + 100, duration=0.3)
    time.sleep(0.3)
    
    # First click ensures canvas has active mouse focus, second click performs the fill
    pyautogui.click(canvas_x + 100, canvas_y + 100)
    time.sleep(0.2)
    pyautogui.click(canvas_x + 100, canvas_y + 100)
    time.sleep(2)
    return f"Successfully filled with colour: {color}!"

def draw_and_fill_logic(shape: str, color: str) -> str:
    """
    Draw the specified shape and then fill it with the given colour.
    Returns a combined success message or the error from the first step.
    """
    # First draw the shape
    draw_result = draw_shape_logic(shape)
    if not draw_result.startswith("Successfully drew"):
        return draw_result
    # Then fill the shape with colour
    fill_result = fill_color_logic(color)
    return f"{draw_result} Then {fill_result}"
