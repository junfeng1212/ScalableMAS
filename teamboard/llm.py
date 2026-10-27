"""LLM adapters. Each one keeps the conversation in its provider's native format behind one small interface:

    add_user(text)                          append a user message
    add_tool_results([(call_id, output)])   append the outputs of the tool calls of the last reply
    await step() -> LLMReply                call the model once and append its reply to the history
"""

import json
import os
from dataclasses import dataclass

import anthropic
import openai


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON schema of the arguments


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict | str  # a str means the model produced arguments that are not valid JSON


@dataclass
class LLMReply:
    text: str
    tool_calls: list[ToolCall]
    usage: dict
    stop_reason: str
    reasoning: str = ""


def parse_arguments(raw: str) -> dict | str:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return raw


def client_kwargs(cfg: dict) -> dict:
    kwargs = dict(cfg.get("client") or {})
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    if cfg.get("api_key"):  # the key written in the YAML
        kwargs["api_key"] = cfg["api_key"]
    elif cfg.get("api_key_env"):  # the name of the environment variable holding the key
        kwargs["api_key"] = os.environ.get(cfg["api_key_env"], "EMPTY")
    return kwargs


class ClaudeLLM:
    """Anthropic Messages API. The history is append-only, so thinking blocks stay valid across steps."""

    def __init__(self, cfg: dict, system_prompt: str, tool_specs: list[ToolSpec]):
        self.client = anthropic.AsyncAnthropic(**client_kwargs(cfg))
        self.cfg = cfg
        self.system = system_prompt
        self.tools = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tool_specs]
        self.messages = []

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_tool_results(self, results: list[tuple[str, str]]) -> None:
        content = [{"type": "tool_result", "tool_use_id": call_id, "content": output} for call_id, output in results]
        self.messages.append({"role": "user", "content": content})

    async def step(self) -> LLMReply:
        response = await self.client.beta.messages.create(
            model=self.cfg["model"], system=self.system, tools=self.tools, messages=self.messages, **self.cfg["request"]
        )
        self.messages.append({"role": "assistant", "content": response.content})
        usage = response.usage
        return LLMReply(
            text="".join(block.text for block in response.content if block.type == "text"),
            tool_calls=[ToolCall(b.id, b.name, b.input) for b in response.content if b.type == "tool_use"],
            usage={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": usage.cache_read_input_tokens or 0,
                "cache_creation_input_tokens": usage.cache_creation_input_tokens or 0,
            },
            stop_reason=response.stop_reason,
            reasoning="".join(block.thinking for block in response.content if block.type == "thinking"),
        )


class OpenAIResponsesLLM:
    """OpenAI Responses API. The reasoning stays on OpenAI's side between steps via previous_response_id."""

    def __init__(self, cfg: dict, system_prompt: str, tool_specs: list[ToolSpec]):
        self.client = openai.AsyncOpenAI(**client_kwargs(cfg))
        self.cfg = cfg
        self.system = system_prompt
        self.tools = [
            {"type": "function", "name": t.name, "description": t.description, "parameters": t.parameters, "strict": False}
            for t in tool_specs
        ]
        self.new_input = []  # items not yet sent to the API
        self.previous_response_id = None

    def add_user(self, text: str) -> None:
        self.new_input.append({"role": "user", "content": text})

    def add_tool_results(self, results: list[tuple[str, str]]) -> None:
        self.new_input += [
            {"type": "function_call_output", "call_id": call_id, "output": output} for call_id, output in results
        ]

    async def step(self) -> LLMReply:
        response = await self.client.responses.create(
            model=self.cfg["model"],
            instructions=self.system,
            input=self.new_input,
            tools=self.tools,
            previous_response_id=self.previous_response_id or openai.NOT_GIVEN,
            **self.cfg["request"],
        )
        self.previous_response_id, self.new_input = response.id, []
        return LLMReply(
            text=response.output_text,
            tool_calls=[
                ToolCall(item.call_id, item.name, parse_arguments(item.arguments))
                for item in response.output
                if item.type == "function_call"
            ],
            usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
            stop_reason=response.status,
            reasoning="\n".join(
                part.text for item in response.output if item.type == "reasoning" for part in item.summary
            ),
        )


class ChatCompletionsLLM:
    """OpenAI-compatible Chat Completions: a local vLLM server, or any OpenAI-compatible proxy."""

    def __init__(self, cfg: dict, system_prompt: str, tool_specs: list[ToolSpec]):
        self.client = openai.AsyncOpenAI(**client_kwargs(cfg))
        self.cfg = cfg
        # Field under which the thinking of earlier steps is sent back: "reasoning" for vLLM (fed to the chat
        # template, e.g. Qwen3.8 preserved thinking), "reasoning_content" for DeepSeek (required with tools).
        self.reasoning_key = cfg["reasoning_key"]
        self.tools = [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in tool_specs
        ]
        self.messages = [{"role": "system", "content": system_prompt}]

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_tool_results(self, results: list[tuple[str, str]]) -> None:
        self.messages += [{"role": "tool", "tool_call_id": call_id, "content": output} for call_id, output in results]

    async def step(self) -> LLMReply:
        response = await self.client.chat.completions.create(
            model=self.cfg["model"], messages=self.messages, tools=self.tools, **self.cfg["request"]
        )
        choice = response.choices[0]
        message = choice.message
        tool_calls = message.tool_calls or []
        # The thinking comes back as `reasoning` (vLLM >= 0.11) or `reasoning_content` (older vLLM, DeepSeek).
        reasoning = getattr(message, "reasoning", None) or getattr(message, "reasoning_content", None) or ""
        assistant = {"role": "assistant", "content": message.content or ""}
        if reasoning:
            assistant[self.reasoning_key] = reasoning
        if tool_calls:
            assistant["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        self.messages.append(assistant)
        return LLMReply(
            text=message.content or "",
            tool_calls=[ToolCall(tc.id, tc.function.name, parse_arguments(tc.function.arguments)) for tc in tool_calls],
            usage={"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens},
            stop_reason=choice.finish_reason,
            reasoning=reasoning,
        )


PROVIDERS = {
    "anthropic": ClaudeLLM,
    "openai": OpenAIResponsesLLM,
    "vllm": ChatCompletionsLLM,
    "openai_chat": ChatCompletionsLLM,  # e.g. an OpenAI-compatible proxy that has no Responses API
}


def make_llm(cfg: dict, system_prompt: str, tool_specs: list[ToolSpec]):
    return PROVIDERS[cfg["provider"]](cfg, system_prompt, tool_specs)
