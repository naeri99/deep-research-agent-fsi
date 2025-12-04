import json
import asyncio
from typing import Dict, Any, Union
import sys
import io


# ============================================================================
# ParallelStrand - 완벽한 버전
# ============================================================================

class ParallelStrand:
    """여러 Agent를 병렬로 실행 (출력 숨김)"""
    
    def __init__(self, agents: Dict[str, Any]):
        self.agents = agents
    
    async def _run_agent(self, name: str, agent: Any, query: str) -> tuple:
        """단일 Agent 실행 (출력 숨김)"""
        try:
            # 출력 숨기기
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            agent_stream = agent.stream_async(query)
            full_response = ""
            
            async for event in agent_stream:
                if "data" in event:
                    full_response += event["data"]
            
            # 출력 복원
            sys.stdout = old_stdout
            
            return (name, full_response.strip())
            
        except Exception as e:
            sys.stdout = old_stdout
            return (name, f"Error: {str(e)}")
    
    async def invoke(self, queries: Union[str, Dict[str, any]]) -> Dict[str, str]:
        """병렬 실행"""
        # 쿼리 처리
        if isinstance(queries, str):
            query_dict = {name: queries for name in self.agents.keys()}
        elif isinstance(queries, dict):
            query_dict = queries
        else:
            raise ValueError("queries는 문자열 또는 딕셔너리여야 합니다")
        
        # 병렬 실행
        tasks = []
        for name, agent in self.agents.items():
            query = query_dict.get(name, "")
            if query:
                tasks.append(self._run_agent(name, agent, query))
        
        results = await asyncio.gather(*tasks)
        
        return {name: response for name, response in results}



