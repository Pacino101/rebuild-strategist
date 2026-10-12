#!/usr/bin/env python3
"""
REBUILD Provider Adapter — a pluggable model-calling layer.

Design goal: anyone who clones this repository can plug in any API of their own
and run REBUILD without modifying a single line of code. Standard library only;
third-party libraries such as requests are optional.

Two ways to connect:
  1. manual   manual mode (default, zero configuration) — render the prompt,
              paste it by hand, paste the output back
  2. http     HTTP mode — talk to any OpenAI-compatible / Anthropic-compatible
              endpoint

Why this is not an SDK dependency:
  Marketing practitioners are more at home on the command line than in a Python
  environment. Any step that requires pip install sharply raises the drop-off
  rate. The standard-library urllib is enough for the overwhelming majority of
  API calls.
"""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Known provider presets. Users may add more, as long as field semantics match.
PROVIDER_PRESETS = {
    "openai": {
        "label": "OpenAI",
        "api_style": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "api_style": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "moonshot": {
        "label": "Moonshot / Kimi",
        "api_style": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "api_key_env": "MOONSHOT_API_KEY",
    },
    "qwen": {
        "label": "Alibaba Qwen",
        "api_style": "dashscope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "api_style": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "ollama": {
        "label": "Ollama local model",
        "api_style": "openai",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:14b",
        "api_key_env": "OLLAMA_API_KEY",  # a local server usually needs no real key
    },
    "custom": {
        "label": "Custom endpoint",
        "api_style": "openai",
        "base_url": "",
        "model": "",
        "api_key_env": "CUSTOM_API_KEY",
    },
}


@dataclass
class ProviderConfig:
    """All model parameters needed for one run. Fields mirror PROVIDER_PRESETS."""
    name: str = "manual"
    label: str = "Manual mode"
    api_style: str = "manual"
    base_url: str = ""
    model: str = ""
    api_key_env: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    max_retries: int = 3
    extra_headers: dict = field(default_factory=dict)

    @classmethod
    def from_preset(cls, name):
        preset = PROVIDER_PRESETS.get(name)
        if preset is None:
            raise ValueError(
                f"unknown provider: {name}. Available: {', '.join(PROVIDER_PRESETS)}"
            )
        return cls(name=name, **preset)

    @classmethod
    def from_file(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)

    @property
    def needs_api(self):
        return self.api_style != "manual"

    def resolve_api_key(self):
        if not self.needs_api:
            return None
        if self.api_style == "openai" or self.name == "ollama":
            key = os.environ.get(self.api_key_env, "")
            if key:
                return key
            if self.name == "ollama":
                return "ollama"  # from a local server, any placeholder value will do
            raise RuntimeError(
                f"environment variable {self.api_key_env} is not set.\n"
                f"Run export {self.api_key_env}=your-key first, or switch to manual mode."
            )
        return os.environ.get(self.api_key_env, "")

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Call implementations
# ---------------------------------------------------------------------------

def _post_json(url, headers, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _call_openai_style(config, prompt):
    """Covers OpenAI / DeepSeek / Qwen / Ollama and other compatible endpoints."""
    key = config.resolve_api_key()
    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        **config.extra_headers,
    }
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    result = _post_json(url, headers, payload, config.timeout)
    return result["choices"][0]["message"]["content"], _extract_usage(result)


def _call_anthropic(config, prompt):
    key = config.resolve_api_key()
    url = config.base_url.rstrip("/") + "/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        **config.extra_headers,
    }
    payload = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    result = _post_json(url, headers, payload, config.timeout)
    return ("".join(block.get("text", "") for block in result["content"]),
            _extract_usage(result))


CALLERS = {
    "openai": _call_openai_style,
    "dashscope": _call_openai_style,
    "anthropic": _call_anthropic,
}


def _extract_usage(result) -> dict:
    """Read token usage out of an API response.

    **If it cannot be read, returns available=False. Never estimate.** An
    estimated token count would be written into the report as actual cost,
    which is worse than having no number at all.

    OpenAI-compatible endpoints use prompt_tokens / completion_tokens;
    Anthropic uses input_tokens / output_tokens. Both normalise to one shape.
    """
    usage = (result or {}).get("usage")
    if not isinstance(usage, dict):
        return {"available": False, "reason": "the response contains no usage field"}

    prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    if total is None and isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        total = prompt_tokens + completion_tokens

    if prompt_tokens is None and completion_tokens is None:
        return {"available": False, "reason": "a usage field exists but holds no recognisable token counts",
                "raw": usage}

    return {
        "available": True,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "raw": usage,
    }


def complete(config, prompt):
    """Unified call entry point. Includes exponential-backoff retries."""
    if not config.needs_api:
        raise RuntimeError("manual mode does not call the API; use the render_prompt flow")

    caller = CALLERS.get(config.api_style)
    if caller is None:
        raise ValueError(f"unsupported api_style: {config.api_style}")

    text, _ = complete_with_usage(config, prompt)
    return text


def complete_with_usage(config, prompt):
    """Same as complete, but also returns token usage: `(text, usage)`.

    When usage cannot be read, `usage["available"]` is False — the caller should
    record "no usage obtained this time" honestly instead of filling in an
    estimate.
    """
    if not config.needs_api:
        raise RuntimeError("manual mode does not call the API; use the render_prompt flow")

    caller = CALLERS.get(config.api_style)
    if caller is None:
        raise ValueError(f"unsupported api_style: {config.api_style}")

    last_error = None
    for attempt in range(1, config.max_retries + 1):
        try:
            return caller(config, prompt)
        except urllib.error.HTTPError as exc:
            # Reading the error response body can fail in rare cases (for
            # example an HTTPError carrying no fp — Python 3.9 raises KeyError
            # here). If it cannot be read, treat it as no body: crashing the
            # whole call just to read an error message is mistaking the means
            # for the end.
            try:
                body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:  # noqa: BLE001
                body = ""
            # 4xx is mostly a configuration or quota problem, so retrying is pointless
            if 400 <= exc.code < 500 and exc.code not in (429,):
                raise RuntimeError(
                    f"HTTP {exc.code}: {body}\n"
                    f"Check whether base_url, the model name and the key are correct."
                ) from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc

        if attempt < config.max_retries:
            wait = 2 ** attempt
            print(f"  call failed ({last_error}); retrying in {wait}s "
                  f"[{attempt}/{config.max_retries}]")
            time.sleep(wait)

    raise RuntimeError(f"still failing after {config.max_retries} retries: {last_error}")


def check_available(config):
    """Pre-flight check: is the configuration usable? Returns (usable, note).

    The check order is deliberate: structural errors first (missing base_url /
    model), credentials second. That way users of a custom provider see the
    problem they actually need to fix, instead of being misled by "key not set".
    """
    if not config.needs_api:
        return True, "manual mode needs no pre-flight check"
    if not config.base_url:
        return False, "base_url is empty; use the custom provider and pass --base-url"
    if not config.model:
        return False, "model is empty; specify --model in the configuration"
    try:
        key = config.resolve_api_key()
    except RuntimeError as exc:
        return False, str(exc)
    if not key:
        return False, f"key is empty ({config.api_key_env})"
    return True, f"{config.label} · {config.model}"


def _pad(text, width):
    """Pad to a display width: Chinese characters take 2 columns, Latin
    letters and digits 1."""
    display = sum(2 if ord(c) > 0x2E7F else 1 for c in text)
    return text + " " * max(0, width - display)


def describe_providers():
    """List every known provider, for the CLI to display."""
    lines = ["Available provider presets:", ""]
    for name, preset in PROVIDER_PRESETS.items():
        env = preset.get("api_key_env", "")
        if preset["api_style"] == "manual":
            needs = "no key needed"
        elif name == "ollama":
            needs = "runs locally, usually no key needed"
        else:
            needs = f"needs {env}"
        lines.append(f"  {_pad(name, 13)}{_pad(preset['label'], 22)}{needs}")
    lines += [
        "",
        "Usage:",
        "  python bench/provider.py check deepseek",
        "  export DEEPSEEK_API_KEY=sk-xxx",
        "  python bench/provider.py call deepseek --prompt-file prompt.txt",
        "",
        "Custom OpenAI-compatible endpoint:",
        "  python bench/provider.py call custom \\",
        "      --base-url https://your-endpoint/v1 \\",
        "      --model your-model \\",
        "      --api-key-env YOUR_KEY",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="REBUILD model adapter: check configuration and try a single call"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list all provider presets")

    c = sub.add_parser("check", help="pre-flight check one provider configuration")
    c.add_argument("provider")

    p = sub.add_parser("call", help="make one test call to any provider")
    p.add_argument("provider")
    p.add_argument("--prompt-file", required=True, help="path to the prompt file")
    p.add_argument("--base-url", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--api-key-env", default=None)
    p.add_argument("--api-style", default=None, choices=list(CALLERS) + ["manual"])
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--output", default=None, help="write the result to a file")
    p.add_argument("--timeout", type=int, default=None)

    args = parser.parse_args()

    if args.cmd == "list":
        print(describe_providers())
        return 0

    try:
        config = ProviderConfig.from_preset(args.provider)
    except ValueError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 1

    if args.cmd == "check":
        ok, message = check_available(config)
        print(f"{'✓' if ok else '✗'} {message}")
        return 0 if ok else 1

    if args.cmd == "call":
        for attr in ("base_url", "model", "api_key_env", "api_style",
                     "temperature", "max_tokens", "timeout"):
            value = getattr(args, attr, None)
            if value is not None:
                setattr(config, attr, value)

        ok, message = check_available(config)
        if not ok:
            print(f"configuration check failed: {message}", file=os.sys.stderr)
            return 1
        print(f"using: {message}")

        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        print(f"prompt is {len(prompt)} characters; calling…")

        try:
            text = complete(config, prompt)
        except RuntimeError as exc:
            print(f"call failed: {exc}", file=os.sys.stderr)
            return 1

        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"output written to {args.output} ({len(text)} characters)")
        else:
            print("-" * 60)
            print(text)
        return 0

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
