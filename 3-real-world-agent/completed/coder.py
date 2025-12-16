import logging
from utils.strands_sdk_utils import strands_utils
from prompts.template import apply_prompt_template
from utils.common_utils import get_message_from_string
import asyncio
from tools import python_repl_tool, bash_tool

# Tools

# Simple logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def log_node_start(node_name: str):
    """Log the start of a node execution."""
    print()  # Add newline before log
    logger.info(f"{Colors.GREEN}===== {node_name} started ====={Colors.END}")

def log_node_complete(node_name: str):
    """Log the completion of a node."""
    print()  # Add newline before log
    logger.info(f"{Colors.GREEN}===== {node_name} completed ====={Colors.END}")

# Global state storage for sharing between nodes
# 로깅 설정 추가
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# 글로벌 상태 초기화
_global_node_states = {}

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"
FULL_PLAN_FORMAT = "Here is full plan :\n\n<full_plan>\n{}\n</full_plan>\n\n*Please consider this to select the next step.*"
CLUES_FORMAT = "Here is clues from {}:\n\n<clues>\n{}\n</clues>\n\n"



async def coder_node(user_request, task=None, **kwargs):
    """Code node that generate code."""
    log_node_start("Planner")
    global _global_node_states

    _global_node_states = {
    'shared': {
        "request": user_request,
        "messages": [{"content": [{"text": "Do as the user instructe"}]}],
        "history": []
        }
    }

    shared_state = _global_node_states.get('shared', None)

    if not shared_state:
        logger.warning("No shared state found in global storage")
        return None, {"text": "No shared state available"}

    agent = strands_utils.get_agent(
        agent_name="coder",
        system_prompts=apply_prompt_template(prompt_name="coder", prompt_context={"USER_REQUEST": user_request, "FULL_PLAN": ""}),
        agent_type="claude-sonnet-4-5", # claude-sonnet-3-5-v-2, claude-sonnet-3-7, claude-sonnet-4
        enable_reasoning=False,
        prompt_cache_info=(True, "default"),  # reasoning agent uses prompt caching
        tools=[python_repl_tool, bash_tool],
        streaming=True  # Enable streaming for consistency
    )

    messages = shared_state["messages"]
    message = messages[-1]["content"][-1]["text"]

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, agent_name="coder_node", source="code_node"
    ):
        if event.get("event_type") == "text_chunk": full_text += event.get("data", "")
    response = {"text": full_text}

    # Update shared global state
    shared_state['messages'] = [get_message_from_string(role="user", string=response["text"], imgs=[])]
    shared_state['full_plan'] = response["text"]
    shared_state['history'].append({"agent":"planner", "message": response["text"]})

    log_node_complete("Planner")
    # Return response only
    return response



if __name__ == "__main__":
    setup_logging()  # 로깅 설정 호출
    result = asyncio.run(coder_node("피바나치 수열 1000 번째 값을 구하는 코드를 구현하고 결과를 주세요 "))
    if result and 'text' in result:
        print(result['text'])
    else:
        print(result)