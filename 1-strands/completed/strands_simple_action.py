"""
strands_simple_action.py

Strands Agents SDK를 사용하여 ReAct 프레임 워크 실험
"""

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



system_prompt = """당신은 일정 관리 도우미입니다.

사용자가 선택할 수 있는 행동 목록:
1. **음식을 섭취한다** - 피자와 치킨을 먹는다
2. **운동을 한다** - 축구를 한다
3. **공부를 한다** - 수학과 영어를 공부한다

사용자의 상황을 파악하고 위 행동 중 가장 적절한 것을 선택해주세요.

응답 형식:
- 선택한 행동 번호와 이름
- 선택 이유
- 간단한 조언
"""

agent = Agent(
    model=bedrock_model,
    callback_handler=None,
    system_prompt=system_prompt
    )



async def run_agent(user_input):
    output = ""
    async for event in agent.stream_async(user_input):
        if "data" in event:
            output += event["data"]
            print(event["data"], end="", flush=True)
    print()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Agent CLI")
    parser.add_argument("query", help="질문 내용")
    args = parser.parse_args()
    
    asyncio.run(run_agent(args.query))








