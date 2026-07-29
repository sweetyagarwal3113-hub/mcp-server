import os
import sys
import asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from pydantic import BaseModel, Field

try:
    from langchain.agents import create_react_agent
except Exception:
    from langgraph.prebuilt import create_react_agent

from browser.browser_tool import get_page_title, get_page_text, screenshot
from paint.paint_tool import draw_shape_logic, fill_color_logic

load_dotenv()

st.set_page_config(page_title="AI Agent MCP Web UI", page_icon="🤖", layout="wide")

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except Exception:
            pass

st.title("🤖 AI Agent MCP Assistant")
st.caption("Powered by LangGraph, FastMCP, Playwright & Groq Llama-3.3")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

@tool("page_title")
async def page_title_tool(url: str) -> str:
    """Read webpage title."""
    return await get_page_title(url)

@tool("read_page")
async def read_page_tool(url: str, scrolls: int = 5) -> str:
    """Read webpage text. Use 'scrolls' to control how many times to scroll down to load more content."""
    return await get_page_text(url, scrolls)

@tool("take_screenshot")
async def take_screenshot_tool(url: str) -> str:
    """Take screenshot of webpage."""
    return await screenshot(url)

@tool("draw_shape")
def draw_shape_tool(shape: str) -> str:
    """Use this tool to draw a shape in MS Paint. Supported shapes: rectangle, smiley, oval."""
    return draw_shape_logic(shape)

@tool("fill_color")
def fill_color_tool(color: str) -> str:
    """Use this tool to fill a shape with a specific color in MS Paint."""
    return fill_color_logic(color)

async def process_user_query(user_prompt: str, api_key: str):
    if not api_key:
        return "Error: GROQ_API_KEY is missing. Please set it in sidebar or environment variables."

    os.environ["GROQ_API_KEY"] = api_key

    langchain_tools = [page_title_tool, read_page_tool, take_screenshot_tool, draw_shape_tool, fill_color_tool]

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, max_retries=3, groq_api_key=api_key)


    profile_url = os.environ.get("LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/me/")
    base_profile_url = profile_url.split("?")[0].rstrip("/")
    my_posts_url = f"{base_profile_url}/recent-activity/all/"

    system_message = f"""You are a helpful AI agent equipped with active execution tools for browser automation and MS Paint drawing.

AVAILABLE TOOLS AND WHEN TO USE THEM:
1. `read_page(url, scrolls=5)`:
   - Use to read and extract text from any webpage URL.
   - If the user asks for "my latest posts", "my posts", "latest posts", or "recent posts", ALWAYS call `read_page` using URL: {my_posts_url}
   - If the user asks for "feed" or "timeline", call `read_page` using URL: https://www.linkedin.com/feed/
   - If the user asks for profile info, call `read_page` using URL: {profile_url}

2. `page_title(url)`:
   - Use to read the title of a webpage URL.

3. `take_screenshot(url)`:
   - Use to capture a screenshot of a webpage URL.

4. `draw_shape(shape)`:
   - Supported shapes: 'rectangle', 'oval', 'smiley'.
   - ONLY call when the user explicitly asks to draw a shape (e.g. "draw a rectangle", "make an oval", "draw a smiley").
   - DO NOT call `draw_shape` for normal conversations, greetings, or saying goodbye!

5. `fill_color(color)`:
   - Supported colors: 'red', 'blue', 'green', 'yellow', etc.
   - ONLY call when the user explicitly asks to fill a shape with a color (e.g. "fill with blue").

CONVERSATION RULES:
- If the user says "bye", "goodbye", "hi", "hello", or asks "what is my name?", respond politely in text WITHOUT calling any tools!
- DO NOT call `brave_search`.
- For real-world leadership updates: Chief Minister of Rajasthan is **Bhajan Lal Sharma**, Prime Minister of India is **Narendra Modi**.
"""

    agent = create_react_agent(llm, tools=langchain_tools)

    final_response = ""
    try:
        async for chunk in agent.astream({"messages": [
            ("system", system_message),
            ("user", user_prompt)
        ]}):
            for node_name, node_output in chunk.items():
                if "messages" in node_output:
                    for msg in node_output["messages"]:
                        if msg.type == "ai" and msg.content:
                            final_response = msg.content
    except Exception as err:
        err_str = str(err)
        if "rate_limit_exceeded" in err_str or "429" in err_str:
            # Fallback to ultra-fast high-capacity llama-3.1-8b-instant model to bypass 70b rate limits!
            try:
                fallback_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, groq_api_key=api_key)
                fallback_agent = create_react_agent(fallback_llm, tools=langchain_tools)
                retry_res = await fallback_agent.ainvoke({"messages": [
                    ("system", system_message),
                    ("user", user_prompt)
                ]})
                if "messages" in retry_res and retry_res["messages"]:
                    return retry_res["messages"][-1].content
            except Exception:
                return "⚠️ **Groq API Rate Limit Reached (Free Tier)**: Please wait a few seconds before asking your next question!"
        elif "tool_use_failed" in err_str or "brave_search" in err_str or "BadRequestError" in err_str:
            fallback_res = await llm.ainvoke([
                ("system", "Answer the user's question directly based on your knowledge."),
                ("user", user_prompt)
            ])
            return fallback_res.content
        else:
            raise err


    return final_response if final_response else "Completed query execution."

# Store API key persistently across Streamlit reruns
if "groq_api_key" not in st.session_state:
    st.session_state.groq_api_key = os.getenv("GROQ_API_KEY", "")

with st.sidebar:
    st.header("⚙️ Configuration")
    user_key_input = st.text_input("Enter Groq API Key:", value=st.session_state.groq_api_key, type="password")
    if user_key_input:
        st.session_state.groq_api_key = user_key_input
        os.environ["GROQ_API_KEY"] = user_key_input
        st.success("GROQ_API_KEY active!")
    else:
        st.warning("Please enter your GROQ_API_KEY or set it in Streamlit Secrets.")

prompt = st.chat_input("Ask the AI Agent anything (e.g. Read https://example.com)...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        current_api_key = st.session_state.groq_api_key or os.getenv("GROQ_API_KEY", "")
        if not current_api_key:
            st.error("Please enter your GROQ_API_KEY in the sidebar to use the agent!")
        else:
            with st.spinner("AI Agent is working..."):
                try:
                    response = run_async(process_user_query(prompt, current_api_key))
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    err_msg = str(e)
                    if hasattr(e, "exceptions") and getattr(e, "exceptions"):
                        sub_errs = "\n".join([str(sub) for sub in getattr(e, "exceptions")])
                        err_msg = f"{e}\nDetails: {sub_errs}"
                    st.error(f"An error occurred while running the agent: {err_msg}")
