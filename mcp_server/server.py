from mcp.server.fastmcp import FastMCP
from browser.browser_tool import get_page_title, get_page_text, screenshot
from paint.paint_tool import draw_shape_logic, fill_color_logic
import pyautogui
import time
import subprocess

mcp = FastMCP("AI Agent MCP Server")

@mcp.tool()
async def page_title(url: str):
    """
    Read webpage title.
    """
    return await get_page_title(url)

@mcp.tool()
async def read_page(url: str, scrolls: int = 5):
    """
    Read webpage. Use 'scrolls' to control how many times to scroll down to load infinite data (default 5).
    """
    return await get_page_text(url, scrolls)

@mcp.tool()
async def take_screenshot(url: str):
    """
    Take screenshot of webpage.
    """
    return await screenshot(url)

@mcp.tool()
def draw_shape(shape: str) -> str:
    """
    Use this tool to draw a shape in MS Paint. Supported shapes: rectangle, smiley, oval.
    """
    return draw_shape_logic(shape)

@mcp.tool()
def fill_color(color: str) -> str:
    """
    Use this tool to fill a shape with a specific color in MS Paint. Call this AFTER calling draw_shape if the user wants to draw AND fill a shape.
    """
    return fill_color_logic(color)

if __name__ == "__main__":
    mcp.run()