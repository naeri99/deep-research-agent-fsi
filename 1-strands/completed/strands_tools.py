"""
strands_tools.py

Strands Agents SDK를 사용하여 Tools 활용 실습
"""

import argparse
from strands import Agent, tool
import boto3
import json
from strands.models import BedrockModel
import asyncio




bedrock_model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-west-2",
    temperature=0.3
)




@tool
def order_food() -> str:
    """음식을 주문합니다. 피자와 치킨을 배달 주문합니다. 배고프거나 식사가 필요할 때 사용하세요."""
    order_url = "https://fake-delivery-api.com/order"
    order_data = {
        "items": ["pizza", "chicken"],
        "address": "서울시 강남구",
        "phone": "010-1234-5678"
    }
    print(f"\n[주문 완료] {order_url}로 주문 요청")
    print(f"주문 내역: {order_data}")
    return "피자와 치킨 주문이 완료되었습니다. 30분 후 도착 예정입니다."

@tool
def invite_soccer() -> str:
    """친구들에게 축구 초대 메시지를 보냅니다. 운동이 필요하거나 축구 경기 준비가 필요할 때 사용하세요."""
    friends = ["철수", "영희", "민수"]
    message = "오늘 저녁 6시에 축구 할래? 운동장에서 보자!"
    print(f"\n[메시지 전송] {friends}에게 초대 메시지 발송")
    print(f"메시지 내용: {message}")
    return f"{', '.join(friends)}에게 축구 초대 메시지를 보냈습니다."

@tool
def schedule_study() -> str:
    """캘린더에 공부 일정을 예약합니다. 수학과 영어 공부 시간을 등록합니다. 시험 준비나 학습이 필요할 때 사용하세요."""
    calendar_event = {
        "title": "수학 & 영어 공부",
        "date": "2025-12-05",
        "time": "19:00-21:00",
        "location": "도서관"
    }
    print(f"\n[캘린더 예약] 일정 등록 완료")
    print(f"일정: {calendar_event}")
    return f"캘린더에 공부 일정이 등록되었습니다: {calendar_event['date']} {calendar_event['time']}"


# tools 리스트는 이제 필요 없음 - @tool 데코레이터가 자동으로 등록
# Agent 생성 시 함수를 직접 전달
tools = [order_food, invite_soccer, schedule_study]



# 4. Agent 생성 (Tools 등록)
system_prompt = """당신은 일정 관리 도우미입니다.

사용자의 상황을 파악하고 가장 적절한 도구를 선택하여 실행해주세요.

사용 가능한 도구:
1. order_food - 음식 주문 (배고플 때)
2. invite_soccer - 축구 초대 (운동이 필요할 때)
3. schedule_study - 공부 일정 예약 (학습이 필요할 때)

도구를 실행한 후 결과를 사용자에게 알려주세요.
"""

agent = Agent(
    model=bedrock_model,
    tools=tools,
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

