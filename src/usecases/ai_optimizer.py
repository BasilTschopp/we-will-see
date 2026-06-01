from models.models import log


_PROMPT = """You are a test automation expert. Optimize the following YAML testcase for reliability.

Apply these rules:
- Remove duplicate consecutive clicks on the same selector
- Remove click steps immediately before a form_input step on the same selector (form_input handles focus itself)
- Add a wait step (method: wait, input_value: '1.0') before clicks that follow a DOM change such as a modal or form opening
- Keep stable selectors unchanged: data-cy, data-test, aria-label, name, and IDs without UUIDs
- Replace dynamic Quasar UUID IDs (pattern: #f_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) with positional selectors like: tbody tr:last-of-type td:nth-of-type(N) input.q-field__native
- Output only valid YAML. No explanations, no markdown code blocks.

YAML to optimize:
"""


def optimize_yaml(yaml_text: str) -> str:
    from adapters.crypto import get_ai_setting
    api_key = get_ai_setting("anthropic_api_key", "").strip()
    if not api_key:
        raise ValueError("No Anthropic API key configured in Settings > AI.")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": _PROMPT + yaml_text}]
    )

    result = message.content[0].text.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    log.info("AI optimization completed.")
    return result
