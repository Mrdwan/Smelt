import json
from dataclasses import dataclass

import litellm

from smelt.exceptions import PlanParseError

_SYSTEM_PROMPT = """\
You are a project planning assistant. Your job is to read a plan and extract \
a flat, ordered list of concrete, actionable development steps.

Rules:
- Each step must be a single, self-contained task a developer can act on.
- Use plain English. No markdown, no numbering, no bullet characters.
- If a section is vague, break it into the smallest sensible concrete steps.
- Preserve completion status: if a step is clearly marked as done (e.g. [x], ✓, \
"completed", struck through), set done to true.
- Return ONLY a JSON array of objects with "description" and "done" fields, nothing else.

Example output:
[
  {"description": "Create the users table in the database", "done": true},
  {"description": "Add password hashing to the auth module", "done": false}
]
"""


@dataclass
class ParsedStep:
    description: str
    done: bool


class PlanParserAgent:
    def __init__(self, model: str, api_key: str | None = None) -> None:
        self._model = model
        self._api_key = api_key

    def parse(self, content: str) -> list[ParsedStep]:
        """Parse a plan document and return a list of steps with completion status."""
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        }
        if self._api_key is not None:
            kwargs["api_key"] = self._api_key

        try:
            response = litellm.completion(**kwargs)
        except Exception as e:
            raise PlanParseError(f"LLM call failed: {e}") from e

        raw = response.choices[0].message.content or ""

        try:
            items = json.loads(raw)
        except json.JSONDecodeError as e:
            raise PlanParseError(f"LLM returned invalid JSON: {raw!r}") from e

        if not isinstance(items, list) or not all(
            isinstance(i, dict) and "description" in i and "done" in i for i in items
        ):
            raise PlanParseError(f"LLM returned unexpected structure: {raw!r}")

        return [
            ParsedStep(description=i["description"].strip(), done=bool(i["done"]))
            for i in items
            if i["description"].strip()
        ]
