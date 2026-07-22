from pywinauto.application import Application
import sys

def dump_ui():
    print("Connecting to Paint...")
    try:
        app = Application(backend="uia").connect(title_re=".*Paint")
        window = app.window(title_re=".*Paint")
        with open("paint_ui.txt", "w", encoding="utf-8") as f:
            # Redirect stdout to file to capture the dump
            sys.stdout = f
            window.print_control_identifiers(depth=4)
            sys.stdout = sys.__stdout__
        print("Successfully saved UI layout to paint_ui.txt!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_ui()
