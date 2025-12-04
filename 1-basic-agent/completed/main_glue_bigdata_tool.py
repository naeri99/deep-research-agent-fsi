import asyncio
from utils.strands_sdk_utils import strands_utils
from prompts.template import apply_prompt_template

agent_name = "toy_agent"

agent = strands_utils.get_agent(
    agent_name=agent_name,
    system_prompts=apply_prompt_template(prompt_name=agent_name, prompt_context={"AGENT_NAME": agent_name}),
    agent_type="claude-sonnet-4",
    enable_reasoning=True,
    prompt_cache_info=(False, None),
    streaming=True,
    tools=["tools.bash_tool", "tools.glue_bigdata_tool"]
)

if __name__ == "__main__":
    user_input = """s3://sungbum-bigdata-test/big_transaction/LI-Medium_Trans.csv 1. 파일메타 데이터를 확인하고 [] 이반칸에 체크 이후 메타 데이터를 바탕으로 s3://sungbum-bigdata-test/big_transaction/LI-Medium_Trans.csv 분석해줘 """

    async def run_streaming():
        async for event in strands_utils.process_streaming_response_yield(
            agent=agent,
            message=user_input,
            agent_name=agent_name,
            source=agent_name
        ):
            strands_utils.process_event_for_display(event)

    asyncio.run(run_streaming())
