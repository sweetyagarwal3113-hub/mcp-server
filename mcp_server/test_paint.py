import pyautogui
import time
import subprocess

def draw_shape_in_paint(shape_name: str):
    """
    Opens Paint, clicks the selected shape from the toolbar based on coordinates,
    and drags to draw it on the canvas.
    """
    # 1. Open and maximize MS Paint
    subprocess.Popen("mspaint.exe")
    time.sleep(2) # Wait for Paint to load
    pyautogui.hotkey('win', 'up') # Maximize the window
    time.sleep(1)

    # 2. Click the shape in the toolbar
    shape = shape_name.lower()
    
    if shape == "rectangle":
        # Using the coordinates you found
        pyautogui.click(x=638, y=102) 
    
    elif shape == "smiley" or shape == "oval":
        # Using the other toolbar coordinates you found
        pyautogui.click(x=706, y=161) 
        
    else:
        return f"Shape '{shape_name}' is not supported yet."

    # Brief pause after clicking the tool
    time.sleep(0.5)

    # 3. Move to the white canvas (using the coordinate you found)
    canvas_x = 974
    canvas_y = 533
    pyautogui.moveTo(canvas_x, canvas_y)
    
    # Click once to ensure MS Paint is the active window and has focus
    pyautogui.click()
    time.sleep(0.5)
    
    # 4. Click and drag to draw the shape!
    # Explicitly holding the mouse down works better in MS Paint
    pyautogui.mouseDown(button='left')
    pyautogui.moveTo(canvas_x + 200, canvas_y + 200, duration=1.0)
    pyautogui.mouseUp(button='left')
    
    return f"Successfully drew a {shape_name}!"

# --- Test it yourself! ---
draw_shape_in_paint("rectangle")
