import asyncio
from utils.strands_sdk_utils import strands_utils
from prompts.template import apply_prompt_template
from tools import python_repl_tool, bash_tool

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

    async def run_streaming():
        async for event in strands_utils.process_streaming_response_yield(
            agent=agent,
            message= """
                ## 체크리스트
                ### 1. 사전 준비
                - [ ] ./artifacts 디렉토리 생성

                ### 2. 데이터 비식별화 (중요: 원본 데이터 분석 금지)
                - [ ] /home/ec2-user/workshop/2-basic-agent/labs/data/ccReport/customer.csv 파일 로드
                - [ ] Client_Num 컬럼 비식별화 처리
                - 비식별화 규칙: `df['Client_Num'] = df['Client_Num'].map(lambda x: '*' * len(str(x)))`
                - 비식별화 처리 전 Client_Num 샘플같은 것 절대로 보여주지 않기
                - 모든 Client_Num 값을 동일 길이의 '*'로 변환
                - [ ] 비식별화 완료된 데이터를 ./artifacts/customer_filtered.csv로 저장
                - [ ] 원본 customer.csv 파일은 분석하지 않고 즉시 비식별화 처리만 수행

                ### 3. 고객 세그먼트 분석 (customer_filtered.csv 기반)
                - [ ] customer_filtered.csv 파일 로드
                - [ ] 고객 그룹별 특성 분석 수행
                - [ ] 주요 패턴 및 인사이트 도출
                - [ ] 세그먼트별 통계 생성

                각 작업 완료 후 [x]로 표시하고 다음 작업으로 진행하세요.

                **주의사항:**
                - customer.csv는 식별화 전 원본 데이터이므로 절대 데이터 분석 금지
                - 분석은 반드시 비식별화가 완료된 customer_filtered.csv로만 수행
                """
                ,
            agent_name=agent_name,
            source=agent_name
        ):
            strands_utils.process_event_for_display(event)

    asyncio.run(run_streaming())






