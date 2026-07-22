import os
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Basic MCP Client setup (if using standard MCP Python client, or simply calling via sub-process)
# Since you have an MCP server, we can create a client to connect to it.
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import sys

load_dotenv()

async def run_agent():
    # 1. Start the MCP Server using stdio
    server_script = os.path.abspath("mcp_server/server.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=env
    )

    print("Connecting to MCP Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected!")

            # 2. Get tools from the MCP server
            mcp_tools = await session.list_tools()
            
            # 3. Create LangChain tools that proxy to the MCP server
            langchain_tools = []
            
            from langchain_core.tools import StructuredTool
            from pydantic import BaseModel, Field

            class UrlArgs(BaseModel):
                url: str = Field(description="The URL of the webpage to process")
                scrolls: int = Field(default=5, description="How many times to scroll down to load more content. Increase this if asked for a large number of posts/connections.")

            class HelloArgs(BaseModel):
                name: str = Field(description="The name to say hello to")

            class AddArgs(BaseModel):
                a: int
                b: int
                
            class DrawShapeArgs(BaseModel):
                shape: str = Field(description="The name of the shape to draw (e.g., 'rectangle', 'smiley', 'oval')")

            # We create a generic wrapper function builder to keep loop context
            def create_tool_wrapper(tool_name, tool_desc, args_schema):
                async def mcp_tool_proxy(**kwargs):
                    result = await session.call_tool(tool_name, arguments=kwargs)
                    
                    # MCP content is usually a list of objects, we format it to a single string
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
                
                proxy_tool = create_tool_wrapper(t.name, t.description, schema)
                langchain_tools.append(proxy_tool)
                print(f"Loaded tool: {t.name}")

            # 4. Set up the LangGraph Agent with Groq
            llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)
            
            profile_url = os.environ.get("LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/me/")
            base_profile_url = profile_url.split("?")[0].rstrip("/")
            my_posts_url = f"{base_profile_url}/recent-activity/all/"
            
            system_message = f"""You are a helpful AI agent with access to browser tools. 
You can read webpages, extract text, and take screenshots.

Here are the user's default LinkedIn URLs:
- Profile: {profile_url}
- My Own Posts: {my_posts_url}
- My Feed (Home page feed): https://www.linkedin.com/feed/
- Network/Connections: https://www.linkedin.com/mynetwork/invite-connect/connections/

Rules for URLs:
- If the user asks for their OWN posts (e.g. "show my posts"), use the "My Own Posts" URL.
- If the user asks for their feed or timeline, use the "My Feed" URL.
- If the user asks to read their profile or network without a URL, automatically use the corresponding URL from the list above.

If the user asks a general knowledge question unrelated to browsing, just answer using your own trained knowledge without using tools.
When extracting information from a webpage, always do your best to summarize and format exactly what the user asks for.
"""

            agent = create_react_agent(llm, tools=langchain_tools)

            # 5. Start interactive chat loop
            print("\n*** Agent is ready! ***")
            print("Try asking things like:")
            print("- 'Go to my feed at https://www.linkedin.com/feed/ and show me the top 3 posts'")
            print(f"- 'Read https://www.linkedin.com/in/sweety-agarwal-b9265632b and show me just my latest post'")
            print("Type 'exit' to quit.\n")
            
            while True:
                user_text = input("You: ")
                if user_text.strip().lower() in ["exit", "quit", "q"]:
                    break
                    
                if not user_text.strip():
                    continue
                
                try:
                    print("\nAgent Execution Trace:")
                    async for chunk in agent.astream({"messages": [
                        ("system", system_message),
                        ("user", user_text)
                    ]}):
                        for node_name, node_output in chunk.items():
                            if "messages" in node_output:
                                for msg in node_output["messages"]:
                                    if msg.type == "ai":
                                        if msg.content:
                                            print(f"\nAI: {msg.content}")
                                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                                            print(f"\n[Tool Execution]: {msg.tool_calls}")
                                    elif msg.type == "tool":
                                        print(f"[Tool finished executing]")
                            print("-" * 20)
                    print("\n")
                except Exception as e:
                    if "tool_use_failed" in str(e) or "BadRequestError" in str(e):
                        print("\n[!] The AI model made a syntax error when trying to use the tool (this is a known glitch with Groq/Llama3 tool parsing). Please just press enter and try asking your question again!")
                    else:
                        print(f"\n[!] An error occurred: {e}")

if __name__ == "__main__":
    # Ensure nest_asyncio is installed if using jupyter/nested loops: pip install nest-asyncio
    asyncio.run(run_agent())
