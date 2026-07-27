from paint.paint_tool import draw_and_fill_shape_logic
import sys

try:
    res = draw_and_fill_shape_logic("rectangle", "red")
    print("Result:", res)
except Exception as e:
    print("Exception:", e)
