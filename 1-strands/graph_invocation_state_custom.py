from strands import Agent
from strands.multiagent import GraphBuilder
from strands.multiagent.base import MultiAgentBase, NodeResult, Status, MultiAgentResult
from strands.agent.agent_result import AgentResult
from strands.types.content import ContentBlock, Message
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="ap-northeast-2",
    temperature=0.3
)

# Custom FunctionNode with invocation_state
class FunctionNode(MultiAgentBase):
    """Execute deterministic Python functions with invocation_state access."""

    def __init__(self, func, name: str = None):
        super().__init__()
        self.func = func
        self.name = name or func.__name__

    async def invoke_async(self, task, invocation_state=None, **kwargs):
        # Execute function with invocation_state
        result = self.func(task if isinstance(task, str) else str(task), invocation_state)

        agent_result = AgentResult(
            stop_reason="end_turn",
            message=Message(role="assistant", content=[ContentBlock(text=str(result))]),
            input_tokens=0,
            output_tokens=0,
            total_tokens=0
        )

        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(
                result=agent_result,
                status=Status.COMPLETED,
                execution_time=0
            )},
            execution_order=[],
            total_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
            execution_time=0,
            invocation_state=invocation_state
        )

# Custom functions that use invocation_state
def collect_entities(text: str, invocation_state: dict) -> str:
    """Extract and collect entities to invocation_state."""
    # Simple entity extraction (in real case, use NLP)
    words = text.split()
    entities = [w for w in words if w[0].isupper() and len(w) > 2]
    
    collected = invocation_state.get("entities", [])
    collected.extend(entities)
    invocation_state["entities"] = collected
    
    print(f"✓ Collected entities: {entities}")
    return f"Collected {len(entities)} entities"

def collect_relations(text: str, invocation_state: dict) -> str:
    """Extract and collect relations to invocation_state."""
    # Simple relation extraction
    if "integrates with" in text:
        parts = text.split("integrates with")
        if len(parts) == 2:
            source = parts[0].strip().split()[-1]
            target = parts[1].strip().split()[0]
            
            relations = invocation_state.get("relations", [])
            relations.append({"source": source, "target": target, "relation": "integrates_with"})
            invocation_state["relations"] = relations
            
            print(f"✓ Collected relation: {source} -> {target}")
            return f"Collected 1 relation"
    
    return "No relations found"

def summarize_graph(text: str, invocation_state: dict) -> str:
    """Summarize collected graph data from invocation_state."""
    entities = invocation_state.get("entities", [])
    relations = invocation_state.get("relations", [])
    
    summary = f"\n=== Graph Summary ===\n"
    summary += f"Entities ({len(entities)}): {entities}\n"
    summary += f"Relations ({len(relations)}): {relations}"
    
    print(summary)
    return summary

# Create FunctionNodes
entity_collector = FunctionNode(func=collect_entities, name="entity_collector")
relation_collector = FunctionNode(func=collect_relations, name="relation_collector")
summarizer = FunctionNode(func=summarize_graph, name="summarizer")

# Build graph
builder = GraphBuilder()

builder.add_node(entity_collector, "collect_entities")
builder.add_node(relation_collector, "collect_relations")
builder.add_node(summarizer, "summarize")

builder.add_edge("collect_entities", "collect_relations")
builder.add_edge("collect_relations", "summarize")

builder.set_entry_point("collect_entities")

graph = builder.build()

# Execute with invocation_state
if __name__ == "__main__":
    result = graph(
        "AWS Lambda integrates with Amazon S3 and DynamoDB stores data.",
        invocation_state={"entities": [], "relations": []}
    )
    
    print("\n=== Final Result ===")
    print(f"Status: {result.status}")
    print(f"Execution order: {[node.node_id for node in result.execution_order]}")
    print(f"\nFinal State:")
    print(f"Entities: {result.invocation_state.get('entities')}")
    print(f"Relations: {result.invocation_state.get('relations')}")
