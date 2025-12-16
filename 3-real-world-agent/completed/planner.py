import logging
from utils.strands_sdk_utils import strands_utils
from prompts.template import apply_prompt_template
from utils.common_utils import get_message_from_string
import asyncio
# Tools
from tools import coder_agent_tool, reporter_agent_tool, tracker_agent_tool, validator_agent_tool

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


async def planner_node(user_request , task=None, **kwargs):

    """Planner node that generates detailed plans for task execution."""
    log_node_start("Planner")
    global _global_node_states

    _global_node_states = {
    'shared': {
        "request": user_request,
        "messages": [{"content": [{"text": "Start planning"}]}],
        "history": []
        }
    }

    shared_state = _global_node_states.get('shared', None)

    if not shared_state:
        logger.warning("No shared state found in global storage")
        return None, {"text": "No shared state available"}

    agent = strands_utils.get_agent(
        agent_name="planner",
        system_prompts=apply_prompt_template(prompt_name="planner", prompt_context={"USER_REQUEST": user_request}),
        agent_type="claude-sonnet-4", # claude-sonnet-3-5-v-2, claude-sonnet-3-7
        enable_reasoning=True,
        prompt_cache_info=(False, None),  # enable prompt caching for reasoning agent, (False, None), (True, "default")
        streaming=True,
    )

    messages = shared_state["messages"]
    message = messages[-1]["content"][-1]["text"]

    # Process streaming response and collect text in one pass
    full_text = ""
    async for event in strands_utils.process_streaming_response_yield(
        agent, message, agent_name="planner", source="planner_node"
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
    result = asyncio.run(planner_node("은행에서 계좌를 만드는 방법을 알려줘"))
    if result and 'text' in result:
        print(result['text'])
    else:
        print(result)
