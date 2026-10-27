"""The tools an agent can call, and the per-agent Toolbox that executes them."""

from collections import Counter
from functools import partial

from teamboard.llm import ToolCall, ToolSpec

AGENT_TOOLS = [
    ToolSpec(
        "bash",
        "Run a bash command in YOUR private sandbox: a Linux container with python3, working directory "
        "/workspace, no internet. Nobody else can see it. Use it for notes, calculations or text processing.",
        {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The bash command to run."}},
            "required": ["command"],
        },
    ),
    ToolSpec(
        "post_message",
        "Post a message on the public message board, where every teammate can read it. This is the ONLY way "
        "to communicate with your teammates: use it to share your plan, findings (with docids), candidate "
        "answers and objections.",
        {
            "type": "object",
            "properties": {"content": {"type": "string", "description": "The message to post."}},
            "required": ["content"],
        },
    ),
    ToolSpec(
        "read_messages",
        "Read the posts from teammates on the message board that you have not read yet. Call it regularly, "
        "and always before deciding on an answer. If nothing is new and wait_seconds > 0, it waits up to that "
        "long for a teammate to post.",
        {
            "type": "object",
            "properties": {
                "wait_seconds": {
                    "type": "integer",
                    "description": "How long to wait for a new post if there is none yet (0 = do not wait).",
                }
            },
            "required": [],
        },
    ),
    ToolSpec(
        "finish",
        "Submit the final answer. The FIRST call to finish by any agent ends the task for the whole team and "
        "becomes the team's answer, so only call it when the answer is well supported.",
        {
            "type": "object",
            "properties": {
                "explanation": {
                    "type": "string",
                    "description": "Explanation of the final answer, citing evidence docids inline like [20].",
                },
                "exact_answer": {"type": "string", "description": "The succinct, final answer."},
                "confidence": {"type": "string", "description": "Confidence between 0% and 100%, e.g. '80%'."},
            },
            "required": ["explanation", "exact_answer", "confidence"],
        },
    ),
]


BOARD_TOOLS = {"post_message", "read_messages"}  # left out when board.enabled is false


def format_answer(explanation: str, exact_answer: str, confidence: str) -> str:
    """The answer format expected by the BrowseComp-Plus judge."""
    return f"Explanation: {explanation}\nExact Answer: {exact_answer}\nConfidence: {confidence}"


class Toolbox:
    """Executes one agent's tool calls. The board, the retriever and the team are shared with the teammates;
    the sandbox, the read cursor and the statistics belong to this agent only."""

    def __init__(self, name, board, retriever, sandbox, team, board_cfg: dict):
        self.name = name
        self.board = board
        self.retriever = retriever
        self.sandbox = sandbox
        self.team = team
        self.notify_unread = board_cfg["notify_unread"]
        self.max_wait_seconds = board_cfg["max_wait_seconds"]

        self.read_cursor = 0  # id of the last board message this agent has read
        self.call_counts = Counter()
        self.retrieved_docids = set()
        self.finished = False

        agent_tools = [t for t in AGENT_TOOLS if board_cfg["enabled"] or t.name not in BOARD_TOOLS]
        self.specs = retriever.tool_specs + agent_tools
        self.handlers = {spec.name: partial(self.retrieve, spec.name) for spec in retriever.tool_specs}
        self.handlers |= {
            "bash": self.bash,
            "post_message": self.post_message,
            "read_messages": self.read_messages,
            "finish": self.finish,
        }

    async def execute(self, call: ToolCall) -> str:
        self.call_counts[call.name] += 1
        if call.name not in self.handlers:
            return f"Error: unknown tool {call.name!r}."
        if not isinstance(call.args, dict):
            return f"Error: the arguments are not a valid JSON object: {call.args}"
        try:
            return await self.handlers[call.name](**call.args)
        except Exception as exc:  # a bad call is reported back to the model instead of stopping the agent
            return f"Error: {type(exc).__name__}: {exc}"

    async def retrieve(self, tool_name: str, **args) -> str:
        output, docids = await self.retriever.call(tool_name, args)
        if tool_name == "search":
            self.retrieved_docids.update(docids)
        return output

    async def bash(self, command: str) -> str:
        return await self.sandbox.run(command)

    async def post_message(self, content: str) -> str:
        message = self.board.post(self.name, content)
        return f"Posted as message #{message.id}."

    async def read_messages(self, wait_seconds: int = 0) -> str:
        wait = min(int(wait_seconds), self.max_wait_seconds)
        messages = await self.board.wait_for_unread(self.name, self.read_cursor, wait)
        self.read_cursor = len(self.board.messages)
        if not messages:
            return f"No new messages (waited {wait}s)." if wait else "No new messages."
        return "\n".join(message.render() for message in messages)

    async def finish(self, explanation: str, exact_answer: str, confidence: str) -> str:
        self.finished = True
        self.team.submit(self.name, format_answer(explanation, exact_answer, confidence))
        return "Answer submitted. The task is now over for the whole team."

    def status_note(self, step: int, max_steps: int) -> str:
        """Short reminders appended to the last tool output of a step."""
        notes = []
        unread = len(self.board.unread(self.name, self.read_cursor))
        if self.notify_unread and unread:
            notes.append(f"[Board] {unread} unread message(s) from teammates. Use read_messages to read them.")
        if step == max_steps - 1:
            notes.append("[Step limit] Your next step is your last one: call finish with your best answer.")
        return "\n".join(notes)
