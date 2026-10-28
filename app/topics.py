"""Selectable conversation topics. Every option uses the same AI agent."""

TOPICS: dict[str, str] = {
    "General": "Answer questions across all subjects, without a narrow specialty.",
    "Python": "Prioritize Python programming. Use clear explanations, simple code, and examples.",
    "DevOps": "Prioritize Linux, Git, Docker, CI/CD, observability, and deployment workflows.",
    "AWS": "Prioritize AWS services, architecture, security, pricing caveats, and deployment.",
    "Agentic AI": "Prioritize agents, tool calling, LangGraph, orchestration, and evaluation.",
    "Machine Learning": "Prioritize ML concepts, training, testing, metrics, and practical examples.",
    "Interview Prep": "Prioritize interview preparation, practice questions, and clear explanations.",
    "Science": "Prioritize scientific explanations; distinguish evidence from speculation.",
    "Business": "Prioritize practical business thinking, tradeoffs, costs, and risks.",
}


def get_topic_instruction(topic: str) -> str:
    """Reject unknown topics instead of interpolating arbitrary text into the prompt."""
    if topic not in TOPICS:
        raise ValueError(f"Unsupported topic: {topic}")
    return TOPICS[topic]
