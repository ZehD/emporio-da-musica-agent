"""The tool-calling loop.

Send the conversation and the tool schemas to the model, run whatever tools
it asks for, send the results back, repeat until it answers in text.

`stream()` is the loop. It yields events (text tokens, tool calls, a final
run summary) so the web UI can show them live. `reply()` just collects them.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

from .data import Store, load_store
from .prompts import system_prompt
from .tools import TOOLS, schemas

MAX_TOOL_ROUNDS = 6
FALLBACK = ("Desculpa, me enrolei aqui. Pode repetir a pergunta? "
            "Se preferir, chama a equipe no (67) 3341-4444.")


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: dict
    ms: int = 0


@dataclass
class Run:
    """What happened in one turn: shown in the UI's run inspector."""
    model: str
    message: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    llm_rounds: int = 0
    first_token_ms: int | None = None
    total_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class Agent:
    model: str
    client: OpenAI
    store: Store
    history: list[dict] = field(default_factory=list)
    trace: list[ToolCall] = field(default_factory=list)  # tool calls of the last turn
    runs: list[Run] = field(default_factory=list)

    @classmethod
    def from_env(cls, model: str | None = None) -> "Agent":
        load_dotenv()
        client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"),
        )
        model = model or os.getenv("LLM_MODEL") or "anthropic/claude-haiku-5.5"
        return cls(model=model, client=client, store=load_store())

    def reply(self, user_message: str) -> str:
        return "".join(e["text"] for e in self.stream(user_message) if e["type"] == "token")

    def stream(self, user_message: str):
        run = Run(model=self.model, message=user_message)
        start = time.perf_counter()
        elapsed = lambda: int((time.perf_counter() - start) * 1000)  # noqa: E731
        self.trace = run.tool_calls
        self.history.append({"role": "user", "content": user_message})
        tool_schemas = schemas(self.store)

        for _ in range(MAX_TOOL_ROUNDS):
            run.llm_rounds += 1
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt()}, *self.history],
                tools=tool_schemas,
                temperature=0.3,
                stream=True,
                stream_options={"include_usage": True},
            )
            text, calls = "", {}
            for chunk in response:
                if chunk.usage:
                    run.prompt_tokens += chunk.usage.prompt_tokens or 0
                    run.completion_tokens += chunk.usage.completion_tokens or 0
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    if run.first_token_ms is None:
                        run.first_token_ms = elapsed()
                    text += delta.content
                    yield {"type": "token", "text": delta.content}
                for tc in delta.tool_calls or []:  # tool calls arrive in pieces
                    call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    call["id"] = tc.id or call["id"]
                    call["name"] += (tc.function.name or "") if tc.function else ""
                    call["arguments"] += (tc.function.arguments or "") if tc.function else ""

            message = {"role": "assistant", "content": text or None}
            if calls:
                message["tool_calls"] = [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in calls.values()
                ]
            self.history.append(message)

            if not calls:
                break

            for c in calls.values():
                tool_start = time.perf_counter()
                result = self._run_tool(c["name"], c["arguments"])
                call = run.tool_calls[-1]
                call.ms = int((time.perf_counter() - tool_start) * 1000)
                yield {"type": "tool", **asdict(call)}
                self.history.append({"role": "tool", "tool_call_id": c["id"],
                                     "content": json.dumps(result, ensure_ascii=False)})
        else:
            yield {"type": "token", "text": FALLBACK}

        run.total_ms = elapsed()
        self.runs.append(run)
        yield {"type": "done", "run": asdict(run)}

    def _run_tool(self, name: str, raw_arguments: str) -> dict:
        try:
            arguments = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError:
            arguments = {}
        tool = TOOLS.get(name)
        if tool is None:
            result = {"erro": f"Ferramenta desconhecida: {name}"}
        else:
            try:
                result = tool(self.store, **arguments)
            except Exception as exc:  # a bad argument shouldn't crash the chat
                result = {"erro": f"Falha ao executar {name}: {exc}"}
        self.trace.append(ToolCall(name, arguments, result))
        return result
