import pyautogui
import time
import subprocess

def draw_shape_logic(shape: str) -> str:
    """
    Core logic to draw a specific shape in MS Paint. Supported shapes: rectangle, smiley, oval.
    """
    try:
        from pywinauto.application import Application
    except ImportError:
        return "Please install pywinauto first by running: pip install pywinauto"

    # 1. Open and maximize MS Paint
    subprocess.Popen("mspaint.exe")
    time.sleep(2) # Wait for Paint to load
    
    # 2. Connect to MS Paint via pywinauto
    try:
        app = Application(backend="uia").connect(title_re=".*Paint")
        window = app.window(title_re=".*Paint")
        window.set_focus()
        
        pyautogui.hotkey('win', 'up') # Maximize the window
        time.sleep(1)
        
        # 3. Click the shape using UI Automation
        shape = shape.lower()
        if shape == "rectangle":
            shape_title = "Rectangle"
        elif shape == "oval":
            shape_title = "Oval"
        elif shape == "smiley":
            shape_title = "Five-point star" 
        else:
            shape_title = shape.capitalize()
            
        try:
            # Try to find and click the shape button (Windows 11 UI typically uses ListItem in the gallery)
            window.child_window(title=shape_title, control_type="ListItem").click_input()
        except:
            try:
                # Try Windows 10 style (Button)
                window.child_window(title=shape_title, control_type="Button").click_input()
            except Exception:
                return f"Shape '{shape_title}' could not be found in MS Paint's UI."

    except Exception as e:
        return f"UI Automation failed: {e}"

    time.sleep(0.5)

    # 3. Move to the white canvas
    canvas_x = 974
    canvas_y = 533
    pyautogui.moveTo(canvas_x, canvas_y)
    
    # Click once to ensure MS Paint is the active window and has focus
    pyautogui.click()
    time.sleep(0.5)
    
    # 4. Click and drag to draw the shape!
    pyautogui.mouseDown(button='left')
    pyautogui.moveTo(canvas_x + 200, canvas_y + 200, duration=1.0)
    pyautogui.mouseUp(button='left')
    
    return f"Successfully drew a {shape}!"
