import argparse
from strands import Agent
import boto3
import json
from strands.models import BedrockModel
import asyncio


bedrock_model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-west-2",
    temperature=0.3
)

agent = Agent(
    model=bedrock_model,
    callback_handler=None,
    system_prompt=f"""당신은 금융 전문가입니다. 
                      사용자의 금융 관련 질문을 할경우 
                      정확하고 이해하기 쉽게 답변해주세요."""
    )


async def run_agent(user_input):
    output = ""
    async for event in agent.stream_async(user_input):
        if "data" in event:
            output += event["data"]
            print(event["data"], end="", flush=True)
    print()



# Python 스크립트에서 실행
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Agent CLI")
    parser.add_argument("query", help="질문 내용")
    args = parser.parse_args()
    
    asyncio.run(run_agent(args.query))


