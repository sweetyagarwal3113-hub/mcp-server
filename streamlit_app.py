import os
import sys
import asyncio
import nest_asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

nest_asyncio.apply()
load_dotenv()

st.set_page_config(page_title="AI Agent MCP Web UI", page_icon="🤖", layout="wide")

st.title("🤖 AI Agent MCP Assistant")
st.caption("Powered by LangGraph, FastMCP, Playwright & Groq Llama-3.3")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

class UrlArgs(BaseModel):
    url: str = Field(description="The URL of the webpage to process")
    scrolls: int = Field(default=5, description="How many times to scroll down to load more content.")

class HelloArgs(BaseModel):
    name: str = Field(description="The name to say hello to")

class AddArgs(BaseModel):
    a: int
    b: int

class DrawShapeArgs(BaseModel):
    shape: str = Field(description="The name of the shape to draw (e.g., 'rectangle', 'smiley', 'oval')")

class FillColorArgs(BaseModel):
    color: str = Field(description="The color to fill the shape with (e.g., 'red', 'blue', 'green')")

async def process_user_query(user_prompt: str):
    server_script = os.path.abspath("mcp_server/server.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=env
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            langchain_tools = []

            def create_tool_wrapper(tool_name, tool_desc, args_schema):
                async def mcp_tool_proxy(**kwargs):
                    result = await session.call_tool(tool_name, arguments=kwargs)
                    texts = []
                    for item in result.content:
                        if item.type == "text":
                            texts.append(item.text)
                    return "\n".join(texts) if texts else str(result.content)

                def sync_mcp_tool_proxy(*args, **kwargs):
                    raise NotImplementedError("This tool is async only")

                return StructuredTool.from_function(
                    func=sync_mcp_tool_proxy,
                    coroutine=mcp_tool_proxy,
                    name=tool_name,
                    description=tool_desc or "MCP tool",
                    args_schema=args_schema
                )

            for t in mcp_tools.tools:
                schema = None
                if t.name in ["page_title", "read_page", "take_screenshot"]:
                    schema = UrlArgs
                elif t.name == "hello":
                    schema = HelloArgs
                elif t.name == "add":
                    schema = AddArgs
                elif t.name == "draw_shape":
                    schema = DrawShapeArgs
                elif t.name == "fill_color":
                    schema = FillColorArgs

                proxy_tool = create_tool_wrapper(t.name, t.description, schema)
                langchain_tools.append(proxy_tool)

            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                return "Error: GROQ_API_KEY is missing. Please set it in environment variables."

            llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=groq_api_key)

            profile_url = os.environ.get("LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/me/")
            base_profile_url = profile_url.split("?")[0].rstrip("/")
            my_posts_url = f"{base_profile_url}/recent-activity/all/"

            system_message = f"""You are a helpful AI agent with access to browser tools.
You can read webpages, extract text, and take screenshots.

Here are the user's default LinkedIn URLs:
- Profile: {profile_url}
- My Own Posts: {my_posts_url}
- My Feed: https://www.linkedin.com/feed/

Rules for URLs:
- If the user asks for their OWN posts, use the "My Own Posts" URL.
- If the user asks for their feed or timeline, use the "My Feed" URL.
- Summarize content cleanly.
"""

            agent = create_react_agent(llm, tools=langchain_tools)

            final_response = ""
            async for chunk in agent.astream({"messages": [
                ("system", system_message),
                ("user", user_prompt)
            ]}):
                for node_name, node_output in chunk.items():
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if msg.type == "ai" and msg.content:
                                final_response = msg.content

            return final_response

prompt = st.chat_input("Ask the AI Agent anything (e.g. Read https://example.com)...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI Agent is working..."):
            response = asyncio.run(process_user_query(prompt))
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
