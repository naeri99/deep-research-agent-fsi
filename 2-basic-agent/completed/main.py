import asyncio
from utils.strands_sdk_utils import strands_utils
from prompts.template import apply_prompt_template
from tools import python_repl_tool, bash_tool
import argparse

agent_name = "toy_agent"

agent = strands_utils.get_agent(
    agent_name=agent_name,
    system_prompts=apply_prompt_template(prompt_name=agent_name, prompt_context={"AGENT_NAME": agent_name}),
    agent_type="claude-sonnet-4", # 사용할 LLM 모델 (고성능 추론) 
    enable_reasoning=False, # 추론 기능 비활성화 (빠른 응답) 
    prompt_cache_info=(False, None), # 프롬프트 캐싱 비활성화 (False, None), 활성화 시 (True, "default") 
    streaming=True, # 실시간 응답 스트리밍 활성화
    tools=[python_repl_tool, bash_tool]
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strands Agent CLI")
    parser.add_argument("user_input", help="사용자 질의 내용")
    args = parser.parse_args()

    async def run_streaming():
        async for event in strands_utils.process_streaming_response_yield(
            agent=agent,
            message= """
                ## 체크리스트
                - [ ] /home/ec2-user/workshop/2-basic-agent/labs/data/ccReport 안에 있는 customer.csv 파일 로드 및 비식별화한 후 비식별화가 완료된 파일을 ./artifacts에 customer_filtered.csv로 저장해줘.

                ## 비식별화 규칙을 활용해서 변경해줘
                - Client_Num 컬럼의 모든 값을 '*'로 변환
                - df['Client_Num'] = df['Client_Num'].map(lambda x: '*' * len(str(x)))

                ## 고객 세그먼트 분석 포함 사항
                - 고객 그룹별 특성 분석
                - 주요 패턴 및 인사이트
                - 세그먼트별 통계

                각 작업 완료 후 [x]로 표시하고 다음 작업으로 진행하세요.
                """
                ,
            agent_name=agent_name,
            source=agent_name
        ):
            strands_utils.process_event_for_display(event)

    asyncio.run(run_streaming())



