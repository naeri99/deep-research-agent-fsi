# Yummy Food 마케팅 분석 시스템 아키텍처 상세 분석

## 📋 목차
1. [전체 시스템 흐름](#1-전체-시스템-흐름)
2. [각 노드별 상세 분석](#2-각-노드별-상세-분석)
3. [프롬프트 시스템](#3-프롬프트-시스템)
4. [데이터 흐름](#4-데이터-흐름)

---

## 1. 전체 시스템 흐름

### 1.1 시작점: main.py

```python
# 파일: main.py
# 역할: 애플리케이션 진입점

async def graph_streaming_execution(payload):
    """그래프 스트리밍 실행"""
    
    # 1. 환경 초기화
    _setup_execution()  # artifacts 폴더 삭제, 큐 초기화
    
    # 2. 사용자 쿼리 추출
    user_query = payload.get("user_query", "")
    
    # 3. 그래프 빌드
    graph = build_graph()  # graph/builder.py에서 그래프 구조 생성
    
    # 4. 스트리밍 실행
    async for event in graph.stream_async({
        "request": user_query,
        "request_prompt": f"<user_request>{user_query}</user_request>"
    }):
        yield event
```

**핵심 포인트:**
- `user_query`: 사용자의 원본 요청 (한국어)
- `request_prompt`: XML 태그로 감싼 프롬프트 형식
- `stream_async()`: 비동기 스트리밍으로 실시간 이벤트 전달

---

### 1.2 그래프 구조: graph/builder.py

```python
# 파일: graph/builder.py
# 역할: 워크플로우 그래프 구성

def build_graph():
    """3개 노드로 구성된 그래프 빌드"""
    
    builder = GraphBuilder()
    
    # 노드 추가
    coordinator = FunctionNode(func=coordinator_node, name="coordinator")
    planner = FunctionNode(func=planner_node, name="planner")
    supervisor = FunctionNode(func=supervisor_node, name="supervisor")
    
    builder.add_node(coordinator, "coordinator")
    builder.add_node(planner, "planner")
    builder.add_node(supervisor, "supervisor")
    
    # 엣지 설정
    builder.set_entry_point("coordinator")  # 시작점
    builder.add_edge("coordinator", "planner", condition=should_handoff_to_planner)
    builder.add_edge("planner", "supervisor")
    
    return StreamableGraph(builder.build())
```

**그래프 흐름:**
```
사용자 요청
    ↓
[Coordinator] ← 간단한 인사/복잡한 작업 판단
    ↓ (handoff_to_planner 조건 충족 시)
[Planner] ← 작업 계획 수립
    ↓
[Supervisor] ← 에이전트 도구 실행 및 오케스트레이션
    ↓
결과 반환
```

---

## 2. 각 노드별 상세 분석

### 2.1 Coordinator Node

**파일:** `graph/nodes.py` → `coordinator_node()`

**역할:** 
- 사용자와의 첫 접점
- 간단한 인사는 직접 처리
- 복잡한 작업은 Planner로 핸드오프

**프롬프트:** `prompts/coordinator.md`

```markdown
## Role
Amazon Bedrock Deep Research Agent (Bedrock-Manus)
- 간단한 대화는 직접 처리
- 복잡한 작업은 Planner로 라우팅

## Handoff Criteria
직접 처리:
- 인사말 (hello, hi, 안녕하세요)
- 자기소개 요청
- 부적절한 요청 (정중히 거절)

Planner로 핸드오프:
- 데이터 분석 요청
- 코드 생성 요청
- 다단계 작업
- 기술적 질문
```

**코드 흐름:**

```python
async def coordinator_node(task=None, **kwargs):
    # 1. 사용자 요청 추출
    request = task.get("request", "")
    request_prompt = task.get("request_prompt", request)
    
    # 2. 에이전트 생성
    agent = strands_utils.get_agent(
        agent_name="coordinator",
        system_prompts=apply_prompt_template(
            prompt_name="coordinator", 
            prompt_context={}
        ),
        agent_type="claude-sonnet-4",
        enable_reasoning=False,
        prompt_cache_info=(False, None),
        streaming=True,
    )
    
    # 3. 스트리밍 응답 처리
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, request_prompt, 
        agent_name="coordinator", 
        source="coordinator_node"
    ):
        if event.get("event_type") == "text_chunk": 
            full_text += event.get("data", "")
    
    # 4. 전역 상태 저장
    _global_node_states['shared'] = {
        'messages': agent.messages,
        'request': request,
        'request_prompt': request_prompt,
        'history': [{"agent":"coordinator", "message": full_text}]
    }
    
    return {"text": full_text}
```

**출력 예시:**
```
handoff_to_planner: 네, Yummy food의 마케팅 데이터 분석과 docx 보고서 작성 요청을 받았습니다.
```

**핸드오프 조건 체크:**

```python
def should_handoff_to_planner(_):
    """Coordinator가 handoff를 요청했는지 확인"""
    shared_state = _global_node_states.get('shared', {})
    history = shared_state.get('history', [])
    
    for entry in reversed(history):
        if entry.get('agent') == 'coordinator':
            message = entry.get('message', '')
            return 'handoff_to_planner' in message
    
    return False
```

---

### 2.2 Planner Node

**파일:** `graph/nodes.py` → `planner_node()`

**역할:**
- 복잡한 작업을 단계별 계획으로 분해
- Coder, Validator, Reporter 에이전트 할당
- 체크리스트 형식의 작업 계획 생성

**프롬프트:** `prompts/planner.md`

```markdown
## Role
전략적 계획 에이전트
- 복잡한 데이터 분석/연구 작업을 실행 가능한 계획으로 분해
- Coder, Validator, Reporter 전문 에이전트 오케스트레이션

## Instructions
1. 사용자 요청 분석 → 최종 목표와 결과물 식별
2. 필요한 데이터, 분석, 연구 결정
3. 작업 요구사항에 따라 적절한 전문 에이전트 선택
4. 의존성 기반 작업 순서 결정 (데이터 → 분석 → 검증 → 보고)
5. 각 에이전트에 대한 구체적이고 실행 가능한 하위 작업 생성
6. 필수 워크플로우 규칙 준수 (Coder → Validator → Reporter)

## Task Tracking
- 에이전트 작업을 체크리스트로 구조화: `[ ] 작업 설명`
- 완료된 작업 업데이트: `[x] 작업 설명`
```

**코드 흐름:**

```python
async def planner_node(task=None, **kwargs):
    # 1. 전역 상태에서 요청 가져오기
    shared_state = _global_node_states.get('shared', None)
    request = shared_state.get("request", "")
    
    # 2. 에이전트 생성 (Reasoning 활성화)
    agent = strands_utils.get_agent(
        agent_name="planner",
        system_prompts=apply_prompt_template(
            prompt_name="planner", 
            prompt_context={"USER_REQUEST": request}
        ),
        agent_type="claude-sonnet-4",
        enable_reasoning=True,  # 추론 활성화
        prompt_cache_info=(False, None),
        streaming=True,
    )
    
    # 3. Coordinator의 마지막 메시지 가져오기
    messages = shared_state["messages"]
    message = messages[-1]["content"][-1]["text"]
    
    # 4. 스트리밍 응답 처리
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, 
        agent_name="planner", 
        source="planner_node"
    ):
        if event.get("event_type") == "text_chunk": 
            full_text += event.get("data", "")
    
    # 5. 전역 상태 업데이트
    shared_state['messages'] = [get_message_from_string(
        role="user", 
        string=full_text, 
        imgs=[]
    )]
    shared_state['full_plan'] = full_text  # 전체 계획 저장
    shared_state['history'].append({
        "agent":"planner", 
        "message": full_text
    })
    
    return {"text": full_text}
```

**출력 예시:**

```markdown
# Plan

## thought
Yummy food의 마케팅 데이터 분석 요청입니다. 
1. 데이터 로드 및 다차원 분석 (Coder)
2. 계산 검증 필수 (Validator)
3. docx 보고서 작성 (Reporter)

## title
Yummy Food 소비자 구매 패턴 및 광고 효과 종합 분석

## steps

### 1. Coder: 종합 마케팅 데이터 분석
- [ ] './2-real-world-agent/completed/data/*' 경로의 모든 데이터 파일 로드
- [ ] 소비자 구매 이력 데이터 분석
- [ ] 매체별 광고 데이터 분석
- [ ] 카테고리별 분석
- [ ] 광고 예산 및 집행 기간 총합 계산
- [ ] 시각화 생성
- [ ] 계산 메타데이터 생성

### 2. Validator: 마케팅 지표 및 계산 검증
- [ ] 광고 예산 총액 및 매체별 배분 계산 검증
- [ ] 매출, ROI, 전환율 등 핵심 지표 재계산
- [ ] 인용 메타데이터 생성

### 3. Reporter: Yummy Food 마케팅 분석 보고서 작성
- [ ] 검증된 데이터를 바탕으로 개요 작성
- [ ] 소비자 구매 패턴 섹션 작성
- [ ] 광고 매체별 성과 섹션 작성
- [ ] docx 형식으로 최종 보고서 생성
```

---

### 2.3 Supervisor Node

**파일:** `graph/nodes.py` → `supervisor_node()`

**역할:**
- Planner가 만든 계획 실행
- 적절한 에이전트 도구 선택 및 호출
- 작업 완료 추적

**프롬프트:** `prompts/supervisor.md`

```markdown
## Role
워크플로우 슈퍼바이저
- 전문 에이전트 도구 팀 오케스트레이션
- 데이터 분석 및 연구 계획 실행

## Instructions
- full_plan 분석하여 다음 미완료 작업 식별 (`[ ]` 표시)
- clues 검토하여 완료된 작업과 사용 가능한 컨텍스트 파악
- 작업 요구사항에 따라 적절한 에이전트 도구 선택
- 모든 작업이 완료될 때까지 계속 (`[x]` 표시)

## Workflow Adherence
- full_plan에 정의된 실행 순서 엄격히 준수
- 필수 시퀀스 존중 (Coder → Validator → Reporter)
- 단계 건너뛰기 또는 작업 재정렬 금지
```

**코드 흐름:**

```python
async def supervisor_node(task=None, **kwargs):
    # 1. 전역 상태 가져오기
    shared_state = _global_node_states.get('shared', None)
    
    # 2. 에이전트 생성 (도구 포함)
    agent = strands_utils.get_agent(
        agent_name="supervisor",
        system_prompts=apply_prompt_template(
            prompt_name="supervisor", 
            prompt_context={}
        ),
        agent_type="claude-sonnet-4-5",
        enable_reasoning=False,
        prompt_cache_info=(True, "default"),  # 프롬프트 캐싱 활성화
        tools=[
            coder_agent_tool,      # 데이터 분석
            reporter_agent_tool,   # 보고서 작성
            tracker_agent_tool,    # 작업 추적
            validator_agent_tool   # 계산 검증
        ],
        streaming=True,
    )
    
    # 3. 컨텍스트 준비
    clues = shared_state.get("clues", "")
    full_plan = shared_state.get("full_plan", "")
    messages = shared_state["messages"]
    
    message = '\n\n'.join([
        messages[-1]["content"][-1]["text"],
        FULL_PLAN_FORMAT.format(full_plan),
        clues
    ])
    
    # 4. 스트리밍 응답 처리 (도구 호출 포함)
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, 
        agent_name="supervisor", 
        source="supervisor_node"
    ):
        if event.get("event_type") == "text_chunk": 
            full_text += event.get("data", "")
    
    # 5. 히스토리 업데이트
    shared_state['history'].append({
        "agent":"supervisor", 
        "message": full_text
    })
    
    return {"text": full_text}
```

**Supervisor의 도구 호출 예시:**

```
Analyzing the plan... All tasks show `[ ]` status. 
Starting with the first task: Coder for comprehensive marketing data analysis.

Tool calling → Coder
```

---

## 3. 에이전트 도구 (Agent Tools)

Supervisor가 호출하는 4개의 전문 에이전트 도구입니다.

### 3.1 Coder Agent Tool

**파일:** `tools/coder_agent_tool.py`

**역할:** Python 코드 및 Bash 명령 실행

**프롬프트:** `prompts/coder.md`

**사용 가능한 도구:**
- `python_repl_tool`: Python 코드 실행
- `bash_tool`: Bash 명령 실행

**코드 구조:**

```python
def handle_coder_agent_tool(task: str):
    # 1. 전역 상태에서 컨텍스트 가져오기
    shared_state = _global_node_states.get('shared', None)
    request_prompt = shared_state.get("request_prompt", "")
    full_plan = shared_state.get("full_plan", "")
    clues = shared_state.get("clues", "")
    
    # 2. Coder 에이전트 생성
    coder_agent = strands_utils.get_agent(
        agent_name="coder",
        system_prompts=apply_prompt_template(
            prompt_name="coder", 
            prompt_context={
                "USER_REQUEST": request_prompt,
                "FULL_PLAN": full_plan
            }
        ),
        agent_type="claude-sonnet-4-5",
        enable_reasoning=False,
        prompt_cache_info=(True, "default"),
        tools=[python_repl_tool, bash_tool],  # 코딩 도구
        streaming=True
    )
    
    # 3. 메시지 준비
    messages = shared_state.get("messages", [])
    message = '\n\n'.join([
        messages[-1]["content"][-1]["text"], 
        clues
    ])
    
    # 4. 스트리밍 실행
    async def process_coder_stream():
        full_text = ""
        async for event in strands_utils.process_streaming_response_yield(
            coder_agent, message, 
            agent_name="coder", 
            source="coder_tool"
        ):
            if event.get("event_type") == "text_chunk": 
                full_text += event.get("data", "")
        return {"text": full_text}
    
    response = asyncio.run(process_coder_stream())
    
    # 5. 상태 업데이트
    clues = '\n\n'.join([
        clues, 
        CLUES_FORMAT.format("coder", response["text"])
    ])
    
    shared_state['messages'] = [get_message_from_string(
        role="user", 
        string=RESPONSE_FORMAT.format("coder", response["text"]), 
        imgs=[]
    )]
    shared_state['clues'] = clues
    shared_state['history'].append({
        "agent":"coder", 
        "message": response["text"]
    })
    
    return response['text']
```

**실행 예시:**

Coder는 다음과 같은 작업을 수행합니다:

1. **데이터 로드**

```python
import pandas as pd

df = pd.read_csv('data/yummu/yummy-food-market.csv')
```

2. **분석 수행**
```python
# 매체별 성과 분석
media_performance = df.groupby('매체').agg({
    '광고비용': 'sum',
    '매출액': 'sum',
    '노출수': 'sum'
})
```

3. **시각화 생성**
```python
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.bar(media_performance.index, media_performance['매출액'])
plt.savefig('./artifacts/media_comparison.png')
```

4. **메타데이터 저장**
```python
import json
metadata = {
    "total_ad_cost": 10000000000,
    "total_revenue": 8695000415,
    "roas": 0.87
}
with open('./artifacts/calculation_metadata.json', 'w') as f:
    json.dump(metadata, f)
```

---

계속해서 나머지 에이전트 도구들을 분석하겠습니다.

### 3.2 Validator Agent Tool

**파일:** `tools/validator_agent_tool.py`

**역할:** 계산 검증 및 인용 메타데이터 생성

**프롬프트:** `prompts/validator.md`

**사용 가능한 도구:**
- `python_repl_tool`: 재계산 수행
- `bash_tool`: 파일 확인
- `file_read`: 원본 데이터 읽기

**핵심 기능:**

```python
def handle_validator_agent_tool(task: str):
    # 1. Coder가 생성한 calculation_metadata.json 로드
    # 2. 원본 데이터로 재계산 수행
    # 3. 계산 정확도 검증
    # 4. citations.json 생성 (Reporter용)
    
    validator_agent = strands_utils.get_agent(
        agent_name="validator",
        system_prompts=apply_prompt_template(
            prompt_name="validator",
            prompt_context={
                "USER_REQUEST": request_prompt,
                "FULL_PLAN": full_plan
            }
        ),
        agent_type="claude-sonnet-4",
        tools=[python_repl_tool, bash_tool, file_read],
        streaming=True
    )
```

**검증 프로세스:**

1. **메타데이터 로드**
```python
with open('./artifacts/calculation_metadata.json', 'r') as f:
    calculations = json.load(f)
```

2. **우선순위 필터링**
```python
# 48개 계산 중 고우선순위 20개만 검증
high_priority = [c for c in calculations if c['importance'] == 'high']
selected = high_priority + medium_priority[:5]
```

3. **재계산 및 검증**
```python
df = pd.read_csv('./data/yummy-food-market.csv')
verified_total = df['광고비용'].sum()  # 10,000,000,000
original_total = calculations['total_ad_cost']  # 10,000,000,000
assert verified_total == original_total
```

4. **인용 생성**
```python
citations = {
    "metadata": {
        "generated_at": "2025-11-26 00:37:22",
        "total_calculations": 48,
        "cited_calculations": 20,
        "verified_count": 12
    },
    "citations": [
        {
            "id": 1,
            "calculation_name": "total_ad_cost",
            "value": 10000000000,
            "unit": "원",
            "verification_status": "verified"
        }
    ]
}
```

---

### 3.3 Tracker Agent Tool

**파일:** `tools/tracker_agent_tool.py`

**역할:** 작업 완료 상태 추적 및 업데이트

**프롬프트:** `prompts/tracker.md`

**사용 가능한 도구:** 없음 (순수 추론 에이전트)

**코드 구조:**

```python
def handle_tracker_agent_tool(completed_agent: str, completion_summary: str):
    # 1. 완료된 에이전트와 요약 받기
    # 2. full_plan의 체크리스트 업데이트
    # 3. [ ] → [x] 변환
    
    tracker_agent = strands_utils.get_agent(
        agent_name="tracker",
        system_prompts=apply_prompt_template(
            prompt_name="tracker",
            prompt_context={
                "USER_REQUEST": request_prompt,
                "FULL_PLAN": full_plan
            }
        ),
        agent_type="claude-sonnet-4-5",
        enable_reasoning=False,
        tools=[],  # 도구 없음
        streaming=True
    )
    
    # 메시지 준비
    tracking_message = f"""
    Agent '{completed_agent}' has completed its task.
    Here's what was accomplished:
    
    {completion_summary}
    
    Please update the task completion status accordingly.
    """
```

**업데이트 예시:**

**Before:**
```markdown
### 1. Coder: 종합 마케팅 데이터 분석
- [ ] 데이터 파일 로드
- [ ] 소비자 구매 이력 데이터 분석
- [ ] 매체별 광고 데이터 분석
```

**After:**
```markdown
### 1. Coder: 종합 마케팅 데이터 분석
- [x] 데이터 파일 로드
- [x] 소비자 구매 이력 데이터 분석
- [x] 매체별 광고 데이터 분석
```

---

### 3.4 Reporter Agent Tool

**파일:** `tools/reporter_agent_tool.py`

**역할:** 최종 보고서 생성 (docx 형식)

**프롬프트:** `prompts/reporter.md`

**사용 가능한 도구:**
- `python_repl_tool`: docx 생성 코드 실행
- `bash_tool`: 파일 확인
- `file_read`: 분석 결과 및 인용 읽기

**코드 구조:**

```python
def handle_reporter_agent_tool(task: str):
    reporter_agent = strands_utils.get_agent(
        agent_name="reporter",
        system_prompts=apply_prompt_template(
            prompt_name="reporter",
            prompt_context={
                "USER_REQUEST": request_prompt,
                "FULL_PLAN": full_plan
            }
        ),
        agent_type="claude-sonnet-4-5",
        tools=[python_repl_tool, bash_tool, file_read],
        streaming=True
    )
```

**보고서 생성 프로세스:**

1. **분석 결과 읽기**
```python
with open('./artifacts/all_results.txt', 'r') as f:
    analysis = f.read()
```

2. **인용 메타데이터 읽기**
```python
with open('./artifacts/citations.json', 'r') as f:
    citations = json.load(f)
```

3. **docx 문서 생성**
```python
from docx import Document
from docx.shared import Pt, RGBColor

doc = Document()

# 제목
title = doc.add_heading('Yummy Food 마케팅 분석 보고서', 0)

# 개요
doc.add_paragraph(
    f"100억원의 광고 집행 예산을 4개의 매체에 30일동안 "
    f"카테고리(신선식품, 간편식, 건강식품)에 대하여 광고를 집행한 결과입니다.[1]"
)

# 차트 삽입
doc.add_picture('./artifacts/media_comparison.png', width=Inches(6))

# 참고문헌
doc.add_heading('참고문헌', 1)
for citation in citations['citations']:
    doc.add_paragraph(
        f"[{citation['id']}] {citation['calculation_name']}: "
        f"{citation['value']:,}{citation['unit']}"
    )

doc.save('./artifacts/final_report.docx')
```

---

## 4. 프롬프트 시스템

### 4.1 프롬프트 템플릿 시스템

**파일:** `prompts/template.py`

```python
def apply_prompt_template(prompt_name: str, prompt_context={}) -> str:
    # 1. 프롬프트 파일 읽기
    system_prompts = open(
        os.path.join(os.path.dirname(__file__), f"{prompt_name}.md")
    ).read()
    
    # 2. 컨텍스트 준비
    context = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z")
    }
    context.update(prompt_context)
    
    # 3. 템플릿 변수 치환
    system_prompts = system_prompts.format(**context)
    
    return system_prompts
```

**사용 예시:**

```python
# Planner 프롬프트 생성
system_prompts = apply_prompt_template(
    prompt_name="planner",
    prompt_context={
        "USER_REQUEST": "Yummy food 마케팅 데이터 분석..."
    }
)
```

**결과:**
```markdown
---
CURRENT_TIME: Wed Nov 26 2025 00:26:00 +0000
USER_REQUEST: Yummy food 마케팅 데이터 분석...
---

## Role
You are a strategic planning agent...
```

---

### 4.2 각 에이전트별 프롬프트 구조

#### Coordinator 프롬프트 (`coordinator.md`)

```markdown
## Role
Amazon Bedrock Deep Research Agent (Bedrock-Manus)

## Instructions
- 사용자 언어에 맞춰 응답
- 간단한 인사는 직접 처리
- 복잡한 작업은 Planner로 라우팅

## Handoff Criteria
직접 처리: 인사말, 자기소개
핸드오프: 데이터 분석, 코드 생성, 다단계 작업

## Handoff Format
handoff_to_planner: [간단한 확인 메시지]
```

#### Planner 프롬프트 (`planner.md`)

```markdown
## Role
전략적 계획 에이전트

## Instructions
1. 사용자 요청 분석
2. 필요한 데이터/분석 결정
3. 적절한 전문 에이전트 선택
4. 의존성 기반 작업 순서 결정
5. 구체적 하위 작업 생성
6. 필수 워크플로우 규칙 준수

## Task Tracking
- [ ] 미완료 작업
- [x] 완료된 작업
```

#### Supervisor 프롬프트 (`supervisor.md`)

```markdown
## Role
워크플로우 슈퍼바이저

## Instructions
- full_plan에서 다음 미완료 작업 식별
- clues 검토
- 적절한 에이전트 도구 선택
- 모든 작업 완료까지 계속

## Tool Guidance
- coder_agent_tool: 데이터 분석, 계산
- validator_agent_tool: 계산 검증 (필수)
- tracker_agent_tool: 작업 추적
- reporter_agent_tool: 보고서 생성
```

#### Coder 프롬프트 (`coder.md`)

```markdown
## Role
데이터 분석 및 코딩 전문가

## Instructions
- Python/Bash 코드 실행
- 데이터 로드 및 분석
- 시각화 생성
- 계산 메타데이터 생성 (Validator용)

## Tools
- python_repl_tool
- bash_tool
```

#### Validator 프롬프트 (`validator.md`)

```markdown
## Role
계산 검증 및 인용 생성 전문가

## Instructions
- calculation_metadata.json 로드
- 원본 데이터로 재계산
- 정확도 검증
- citations.json 생성

## Tools
- python_repl_tool
- bash_tool
- file_read
```

#### Reporter 프롬프트 (`reporter.md`)

```markdown
## Role
보고서 작성 전문가

## Instructions
- all_results.txt 읽기
- citations.json 읽기
- docx 보고서 생성
- 차트 포함
- 인용 번호 [1], [2] 형식 사용

## Tools
- python_repl_tool
- bash_tool
- file_read
```

---

## 5. 데이터 흐름 및 상태 관리

### 5.1 전역 상태 (_global_node_states)

**파일:** `graph/nodes.py`

```python
# 전역 상태 저장소
_global_node_states = {}

# 구조:
_global_node_states = {
    'shared': {
        'messages': [...],           # 에이전트 메시지 히스토리
        'request': "...",            # 원본 사용자 요청
        'request_prompt': "...",     # 프롬프트 형식 요청
        'full_plan': "...",          # Planner가 생성한 전체 계획
        'clues': "...",              # 누적된 에이전트 응답
        'history': [                 # 대화 히스토리
            {"agent": "coordinator", "message": "..."},
            {"agent": "planner", "message": "..."},
            {"agent": "coder", "message": "..."}
        ]
    }
}
```

### 5.2 데이터 흐름 다이어그램

```
사용자 요청
    ↓
[Coordinator]
    ↓ (전역 상태 초기화)
    messages, request, request_prompt, history
    ↓
[Planner]
    ↓ (계획 추가)
    full_plan 추가
    ↓
[Supervisor]
    ↓ (도구 호출)
    ├─→ [Coder] → clues 업데이트
    │       ↓
    │   artifacts/calculation_metadata.json 생성
    │       ↓
    ├─→ [Tracker] → full_plan 업데이트 ([ ] → [x])
    │       ↓
    ├─→ [Validator] → clues 업데이트
    │       ↓
    │   artifacts/citations.json 생성
    │       ↓
    ├─→ [Tracker] → full_plan 업데이트
    │       ↓
    └─→ [Reporter] → clues 업데이트
            ↓
        artifacts/final_report.docx 생성
```

### 5.3 Clues 누적 패턴

```python
# 초기 상태
clues = ""

# Coder 완료 후
clues = """
Here is clues from coder:

<clues>
✅ 데이터 로드 완료: 720 행, 14 열
총 광고비용: 100.00억원
총 매출액: 86.95억원
</clues>
"""

# Validator 완료 후
clues = """
Here is clues from coder:
<clues>...</clues>

Here is clues from validator:
<clues>
✅ 검증 완료: 검증됨 12개, 검토필요 8개
생성된 인용: 20개 ([1] ~ [20])
</clues>
"""
```

---

## 6. 실행 흐름 요약

### 6.1 전체 실행 시퀀스

```
1. main.py 실행
   ↓
2. graph_streaming_execution() 호출
   ↓
3. build_graph() → StreamableGraph 생성
   ↓
4. graph.stream_async() 시작
   ↓
5. [Coordinator Node]
   - 사용자 요청 분석
   - "handoff_to_planner:" 응답
   - 전역 상태 초기화
   ↓
6. should_handoff_to_planner() 체크 → True
   ↓
7. [Planner Node]
   - 작업 계획 수립
   - full_plan 생성 (체크리스트 형식)
   - 전역 상태에 full_plan 저장
   ↓
8. [Supervisor Node]
   - full_plan 분석
   - 첫 번째 미완료 작업 식별
   ↓
9. Supervisor → coder_agent_tool 호출
   ↓
10. [Coder Agent]
    - 데이터 로드 (yummy-food-market.csv)
    - 분석 수행 (매체별, 카테고리별, 상품별)
    - 시각화 생성 (9개 PNG 파일)
    - calculation_metadata.json 생성
    - clues 업데이트
    ↓
11. Supervisor → tracker_agent_tool 호출
    ↓
12. [Tracker Agent]
    - Coder 작업 완료 확인
    - full_plan 업데이트 ([ ] → [x])
    ↓
13. Supervisor → validator_agent_tool 호출
    ↓
14. [Validator Agent]
    - calculation_metadata.json 로드
    - 원본 데이터로 재계산
    - 검증 수행 (20개 계산)
    - citations.json 생성
    - clues 업데이트
    ↓
15. Supervisor → tracker_agent_tool 호출
    ↓
16. [Tracker Agent]
    - Validator 작업 완료 확인
    - full_plan 업데이트
    ↓
17. Supervisor → reporter_agent_tool 호출
    ↓
18. [Reporter Agent]
    - all_results.txt 읽기
    - citations.json 읽기
    - docx 문서 생성
    - 차트 삽입
    - 인용 추가
    - final_report.docx 저장
    ↓
19. Supervisor → tracker_agent_tool 호출
    ↓
20. [Tracker Agent]
    - Reporter 작업 완료 확인
    - 모든 작업 [x] 확인
    ↓
21. Supervisor 종료
    ↓
22. 최종 결과 반환
```

### 6.2 각 단계별 프롬프트 사용

| 단계 | 노드/도구 | 프롬프트 파일 | 주요 컨텍스트 변수 |
|------|-----------|---------------|-------------------|
| 1 | Coordinator | coordinator.md | - |
| 2 | Planner | planner.md | USER_REQUEST |
| 3 | Supervisor | supervisor.md | - |
| 4 | Coder | coder.md | USER_REQUEST, FULL_PLAN |
| 5 | Tracker | tracker.md | USER_REQUEST, FULL_PLAN |
| 6 | Validator | validator.md | USER_REQUEST, FULL_PLAN |
| 7 | Tracker | tracker.md | USER_REQUEST, FULL_PLAN |
| 8 | Reporter | reporter.md | USER_REQUEST, FULL_PLAN |
| 9 | Tracker | tracker.md | USER_REQUEST, FULL_PLAN |

---

## 7. 핵심 설계 패턴

### 7.1 전역 상태 공유 패턴

```python
# 모든 노드와 도구가 동일한 전역 상태 접근
from graph.nodes import _global_node_states
shared_state = _global_node_states.get('shared', None)
```

### 7.2 스트리밍 응답 패턴

```python
# 모든 에이전트가 동일한 스트리밍 패턴 사용
full_text = ""
async for event in strands_utils.process_streaming_response_yield(
    agent, message, agent_name="...", source="..."
):
    if event.get("event_type") == "text_chunk": 
        full_text += event.get("data", "")
```

### 7.3 컨텍스트 전달 패턴

```python
# 프롬프트 컨텍스트
system_prompts = apply_prompt_template(
    prompt_name="agent_name",
    prompt_context={
        "USER_REQUEST": request_prompt,
        "FULL_PLAN": full_plan
    }
)

# 메시지 컨텍스트
message = '\n\n'.join([
    messages[-1]["content"][-1]["text"],
    FULL_PLAN_FORMAT.format(full_plan),
    clues
])
```

### 7.4 도구 호출 패턴

```python
# Supervisor가 도구 호출
tools=[
    coder_agent_tool,
    validator_agent_tool,
    tracker_agent_tool,
    reporter_agent_tool
]

# 도구 함수 시그니처
def coder_agent_tool(tool: ToolUse, **_kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    task = tool["input"]["task"]
    result = handle_coder_agent_tool(task)
    return {
        "toolUseId": tool_use_id,
        "status": "success",
        "content": [{"text": result}]
    }
```

---

## 8. 결론

이 시스템은 다음과 같은 계층 구조로 동작합니다:

1. **오케스트레이션 레이어** (Coordinator → Planner → Supervisor)
   - 사용자 요청 라우팅
   - 작업 계획 수립
   - 에이전트 도구 실행 관리

2. **실행 레이어** (Coder, Validator, Reporter, Tracker)
   - 실제 작업 수행
   - 데이터 분석, 검증, 보고서 생성
   - 작업 상태 추적

3. **프롬프트 레이어** (템플릿 시스템)
   - 각 에이전트의 역할과 지시사항 정의
   - 컨텍스트 변수 주입

4. **상태 관리 레이어** (전역 상태)
   - 노드 간 데이터 공유
   - 작업 히스토리 관리
   - 누적 컨텍스트 (clues) 관리

각 프로세스는 명확한 프롬프트와 역할을 가지고 있으며, 전역 상태를 통해 서로 협력하여 복잡한 데이터 분석 작업을 완수합니다.
