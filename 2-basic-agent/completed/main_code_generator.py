import asyncio
from utils.strands_sdk_utils import strands_utils
from prompts.template import apply_prompt_template
import argparse


agent_name = "code_agent"

agent = strands_utils.get_agent(
    agent_name=agent_name,
    system_prompts=apply_prompt_template(prompt_name=agent_name, prompt_context={"AGENT_NAME": agent_name}),
    agent_type="claude-sonnet-4", 
    enable_reasoning=False, 
    prompt_cache_info=(False, None),  
    streaming=False, 
)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strands Agent CLI")
    parser.add_argument("user_input", help="사용자 질의 내용")
    args = parser.parse_args()

    async def run_streaming():
        async for event in strands_utils.process_streaming_response_yield(
            agent=agent,
            message=args.user_input,
            agent_name=agent_name,
            source=agent_name
        ):
            strands_utils.process_event_for_display(event)

    asyncio.run(run_streaming())