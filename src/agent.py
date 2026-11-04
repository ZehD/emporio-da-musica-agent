"""The tool-calling loop.

Send the conversation and the tool schemas to the model, run whatever tools
it asks for, send the results back, repeat until it answers in text.
"""

import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

from .data import Store, load_store
from .prompts import system_prompt
from .tools import TOOLS, schemas

MAX_TOOL_ROUNDS = 6


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: dict


@dataclass
class Agent:
    model: str
    client: OpenAI
    store: Store
    history: list[dict] = field(default_factory=list)
    trace: list[ToolCall] = field(default_factory=list)  # tool calls of the last turn

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
        self.trace = []
        self.history.append({"role": "user", "content": user_message})
        tool_schemas = schemas(self.store)

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt()}, *self.history],
                tools=tool_schemas,
                temperature=0.3,
            )
            message = response.choices[0].message
            self.history.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return message.content or ""

            for call in message.tool_calls:
                result = self._run_tool(call.function.name, call.function.arguments)
                self.history.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return ("Desculpa, me enrolei aqui. Pode repetir a pergunta? "
                "Se preferir, chama a equipe no (67) 3341-4444.")

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
