import warnings
warnings.filterwarnings("ignore")

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

            class FillColorArgs(BaseModel):
                color: str = Field(description="The color to fill the shape with (e.g., 'red', 'blue', 'green')")

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
                elif t.name == "fill_color":
                    schema = FillColorArgs
                
                proxy_tool = create_tool_wrapper(t.name, t.description, schema)
                langchain_tools.append(proxy_tool)
                print(f"Loaded tool: {t.name}")

            # 4. Set up the LangGraph Agent with Groq
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, max_retries=3)


            
            profile_url = os.environ.get("LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/me/")
            base_profile_url = profile_url.split("?")[0].rstrip("/")
            my_posts_url = f"{base_profile_url}/recent-activity/all/"
            
            system_message = f"""You are a helpful AI agent equipped with tools for browser automation and MS Paint drawing.

AVAILABLE TOOLS AND WHEN TO USE THEM:
1. `read_page(url, scrolls=5)`:
   - Use ONLY when a URL is explicitly provided by the user, OR when asked for:
     * "my profile" / "profile" (use {profile_url})
     * "my latest posts" / "my posts" (use {my_posts_url})
     * "feed" / "timeline" (use https://www.linkedin.com/feed/)
     * "connections" (use https://www.linkedin.com/mynetwork/invite-connect/connections/)

2. `page_title(url)`:
   - Use ONLY when asked to read a webpage title for a specific URL.

3. `take_screenshot(url)`:
   - Use ONLY when asked to take a screenshot of a specific URL.

4. `draw_shape(shape)`:
   - Supported shapes: 'rectangle', 'oval', 'smiley'.
   - Use ONLY when asked to draw a shape in MS Paint.

5. `fill_color(color)`:
   - Supported colors: 'red', 'blue', 'green', 'yellow', etc.
   - Use ONLY when asked to fill a shape with color in MS Paint.

STRICT EXECUTION RULES:
- USER PROFILE & IDENTITY: If the user asks for their name ("what is my name?", "who am I?"), company/work ("what is my company name?", "where do I work?"), or profile details, call `read_page` with URL {profile_url} to extract the live name, company, and experience details directly from LinkedIn!
- FOR GENERAL KNOWLEDGE QUESTIONS (e.g. "PM of India", "CM of Rajasthan", "What is Python?", "Hello", "Bye"): DO NOT CALL ANY TOOLS! Answer directly using text.
- CRITICAL TOOL RULE: Call a tool AT MOST ONCE per prompt. Once a tool returns a result, IMMEDIATELY output your final response summarizing the result. DO NOT call any tool a second time!
- If `read_page` returns `AUTH_REQUIRED`, inform the user that accessing private LinkedIn content requires logging into LinkedIn in the browser.
- For real-world leadership updates: Prime Minister of India is **Narendra Modi**, Chief Minister of Rajasthan is **Bhajan Lal Sharma**.
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
                    ]}, config={"recursion_limit": 15}):
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
                    err_str = str(e)
                    if "rate_limit_exceeded" in err_str or "429" in err_str:
                        print("\n[!] Groq 70b rate limit hit. Switching to instant fallback model (llama-3.1-8b-instant)...")
                        try:
                            fallback_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, max_retries=3)
                            fallback_agent = create_react_agent(fallback_llm, tools=langchain_tools)
                            retry_res = await fallback_agent.ainvoke({"messages": [
                                ("system", system_message),
                                ("user", user_text)
                            ]})
                            if "messages" in retry_res and retry_res["messages"]:
                                print(f"\nAI: {retry_res['messages'][-1].content}\n")
                        except Exception as err2:
                            print("\n[!] Groq API Rate Limit Reached (Free Tier). Please wait 5 seconds before asking your next question!\n")
                    elif "tool_use_failed" in err_str or "brave_search" in err_str or "BadRequestError" in err_str:
                        print("\n[Direct Answer Fallback]:")
                        fallback_res = await llm.ainvoke([
                            ("system", "Answer the user's question directly based on your knowledge."),
                            ("user", user_text)
                        ])
                        print(f"AI: {fallback_res.content}\n")
                    else:
                        print(f"\n[!] An error occurred: {e}")


if __name__ == "__main__":
    # Ensure nest_asyncio is installed if using jupyter/nested loops: pip install nest-asyncio
    asyncio.run(run_agent())
