#!/usr/bin/env python3
"""
REBUILD Provider Adapter — 可插拔的模型调用层。

设计目标：任何人 clone 本仓库后，接上自己的任意 API 即可运行 REBUILD，
无需修改任何代码。仅依赖 Python 标准库；requests 等第三方库为可选。

支持两类接入方式：
  1. manual   手动模式（默认，零配置）——渲染提示词，人工粘贴，拿回输出
  2. http     HTTP 模式——对接任意 OpenAI 兼容 / Anthropic 兼容端点

为什么不做成 SDK 依赖：
  营销从业者多熟悉命令行而非 Python 环境。任何需要 pip install 的步骤
  都会显著提高放弃率。标准库 urllib 足以覆盖绝大多数 API 调用。
"""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

#: 已知的 provider 预设。用户可新增，字段语义一致即可。
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
        "label": "阿里通义千问",
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
        "label": "Ollama 本地模型",
        "api_style": "openai",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:14b",
        "api_key_env": "OLLAMA_API_KEY",  # 本地通常不需要真 key
    },
    "custom": {
        "label": "自定义 OpenAI 兼容端点",
        "api_style": "openai",
        "base_url": "",
        "model": "",
        "api_key_env": "CUSTOM_API_KEY",
    },
}


@dataclass
class ProviderConfig:
    """一次运行所需的全部模型参数。字段与 PROJVIDER_PRESETS 对应。"""
    name: str = "manual"
    label: str = "手动模式"
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
                f"未知 provider: {name}。可用: {', '.join(PROVIDER_PRESETS)}"
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
                return "ollama"  # 本地服务接受任意占位值
            raise RuntimeError(
                f"未设置环境变量 {self.api_key_env}。\n"
                f"请先 export {self.api_key_env}=你的密钥，或改用手动模式。"
            )
        return os.environ.get(self.api_key_env, "")

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# 调用实现
# ---------------------------------------------------------------------------

def _post_json(url, headers, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _call_openai_style(config, prompt):
    """覆盖 OpenAI / DeepSeek / Qwen / Ollama 等兼容端点。"""
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
    """从 API 响应里取 token 用量。

    **取不到就返回 available=False，绝不估算。** 估出来的 token 数会被当成
    实际成本写进报告，那比没有数字更糟。

    OpenAI 兼容端点用 prompt_tokens / completion_tokens；
    Anthropic 用 input_tokens / output_tokens。统一成同一形状。
    """
    usage = (result or {}).get("usage")
    if not isinstance(usage, dict):
        return {"available": False, "reason": "响应中未包含 usage 字段"}

    prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    if total is None and isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        total = prompt_tokens + completion_tokens

    if prompt_tokens is None and completion_tokens is None:
        return {"available": False, "reason": "usage 字段存在但没有可识别的 token 计数",
                "raw": usage}

    return {
        "available": True,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "raw": usage,
    }


def complete(config, prompt):
    """统一调用入口。含指数退避重试。"""
    if not config.needs_api:
        raise RuntimeError("manual 模式不调用 API，请使用 render_prompt 流程")

    caller = CALLERS.get(config.api_style)
    if caller is None:
        raise ValueError(f"不支持的 api_style: {config.api_style}")

    text, _ = complete_with_usage(config, prompt)
    return text


def complete_with_usage(config, prompt):
    """与 complete 相同，但额外返回 token 用量：`(文本, usage)`。

    用量取不到时 `usage["available"]` 为 False——调用方应如实记录
    「本次未取得用量」，而不是补一个估算值。
    """
    if not config.needs_api:
        raise RuntimeError("manual 模式不调用 API，请使用 render_prompt 流程")

    caller = CALLERS.get(config.api_style)
    if caller is None:
        raise ValueError(f"不支持的 api_style: {config.api_style}")

    last_error = None
    for attempt in range(1, config.max_retries + 1):
        try:
            return caller(config, prompt)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            # 4xx 多为配置或配额问题，重试无意义
            if 400 <= exc.code < 500 and exc.code not in (429,):
                raise RuntimeError(
                    f"HTTP {exc.code}：{body}\n"
                    f"请检查 base_url、model 名称与密钥是否正确。"
                ) from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc

        if attempt < config.max_retries:
            wait = 2 ** attempt
            print(f"  调用失败（{last_error}），{wait}s 后重试 "
                  f"[{attempt}/{config.max_retries}]")
            time.sleep(wait)

    raise RuntimeError(f"重试 {config.max_retries} 次后仍失败：{last_error}")


def check_available(config):
    """预检：配置是否可用。返回 (是否可用, 说明)。

    检查顺序有意为之：先查结构性错误（缺 base_url / model），
    再查凭据。这样 custom provider 的用户会先看到真正要修的问题，
    而不是被"未设置密钥"误导。
    """
    if not config.needs_api:
        return True, "手动模式无需预检"
    if not config.base_url:
        return False, "base_url 为空，请用 custom provider 并指定 --base-url"
    if not config.model:
        return False, "model 为空，请在配置中指定 --model"
    try:
        key = config.resolve_api_key()
    except RuntimeError as exc:
        return False, str(exc)
    if not key:
        return False, f"密钥为空（{config.api_key_env}）"
    return True, f"{config.label} · {config.model}"


def _pad(text, width):
    """按显示宽度补齐：中文占 2 列，英文数字占 1 列。"""
    display = sum(2 if ord(c) > 0x2E7F else 1 for c in text)
    return text + " " * max(0, width - display)


def describe_providers():
    """列出所有已知 provider，供 CLI 展示。"""
    lines = ["可用 provider 预设：", ""]
    for name, preset in PROVIDER_PRESETS.items():
        env = preset.get("api_key_env", "")
        if preset["api_style"] == "manual":
            needs = "无需密钥"
        elif name == "ollama":
            needs = "本地运行，通常无需密钥"
        else:
            needs = f"需要 {env}"
        lines.append(f"  {_pad(name, 13)}{_pad(preset['label'], 22)}{needs}")
    lines += [
        "",
        "用法：",
        "  python bench/provider.py check deepseek",
        "  export DEEPSEEK_API_KEY=sk-xxx",
        "  python bench/provider.py call deepseek --prompt-file prompt.txt",
        "",
        "自定义 OpenAI 兼容端点：",
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
        description="REBUILD 模型接入层：检查配置与单次调用测试"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出所有 provider 预设")

    c = sub.add_parser("check", help="预检某个 provider 配置")
    c.add_argument("provider")

    p = sub.add_parser("call", help="对任意 provider 发起一次测试调用")
    p.add_argument("provider")
    p.add_argument("--prompt-file", required=True, help="提示词文件路径")
    p.add_argument("--base-url", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--api-key-env", default=None)
    p.add_argument("--api-style", default=None, choices=list(CALLERS) + ["manual"])
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--output", default=None, help="结果写入文件")
    p.add_argument("--timeout", type=int, default=None)

    args = parser.parse_args()

    if args.cmd == "list":
        print(describe_providers())
        return 0

    try:
        config = ProviderConfig.from_preset(args.provider)
    except ValueError as exc:
        print(f"错误：{exc}", file=os.sys.stderr)
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
            print(f"配置检查未通过：{message}", file=os.sys.stderr)
            return 1
        print(f"使用：{message}")

        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        print(f"提示词 {len(prompt)} 字符，调用中…")

        try:
            text = complete(config, prompt)
        except RuntimeError as exc:
            print(f"调用失败：{exc}", file=os.sys.stderr)
            return 1

        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"输出已写入 {args.output}（{len(text)} 字符）")
        else:
            print("-" * 60)
            print(text)
        return 0

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
