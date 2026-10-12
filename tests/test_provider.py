"""provider.py 的测试：验证配置解析、密钥处理与调用重试。"""
import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))

import provider


class ProviderConfigTests(unittest.TestCase):
    def test_all_presets_load(self):
        for name in provider.PROVIDER_PRESETS:
            config = provider.ProviderConfig.from_preset(name)
            self.assertEqual(config.name, name)

    def test_unknown_provider_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            provider.ProviderConfig.from_preset("nonexistent")
        self.assertIn("可用", str(ctx.exception))

    def test_ollama_needs_no_key(self):
        config = provider.ProviderConfig.from_preset("ollama")
        self.assertEqual(config.resolve_api_key(), "ollama")

    def test_missing_key_raises_with_guidance(self):
        config = provider.ProviderConfig.from_preset("deepseek")
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                config.resolve_api_key()
        self.assertIn("DEEPSEEK_API_KEY", str(ctx.exception))
        self.assertIn("手动模式", str(ctx.exception))

    def test_manual_mode_needs_no_api(self):
        config = provider.ProviderConfig(api_style="manual")
        self.assertFalse(config.needs_api)
        ok, _ = provider.check_available(config)
        self.assertTrue(ok)

    def test_incomplete_config_fails_check(self):
        config = provider.ProviderConfig.from_preset("custom")
        with mock.patch.dict(os.environ, {}, clear=True):
            ok, message = provider.check_available(config)
        self.assertFalse(ok)
        self.assertIn("base_url", message)


class CallTests(unittest.TestCase):
    def test_manual_mode_refuses_api_call(self):
        config = provider.ProviderConfig(api_style="manual")
        with self.assertRaises(RuntimeError):
            provider.complete(config, "hello")

    def test_unsupported_style_rejected(self):
        config = provider.ProviderConfig(api_style="nonexistent-style")
        with self.assertRaises(ValueError):
            provider.complete(config, "hello")

    def test_openai_payload_shape(self):
        config = provider.ProviderConfig.from_preset("deepseek")
        captured = {}

        def fake_post(url, headers, payload, timeout):
            captured.update(url=url, headers=headers, payload=payload)
            return {"choices": [{"message": {"content": "测试输出"}}]}

        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            with mock.patch.object(provider, "_post_json", fake_post):
                result = provider.complete(config, "提示词")

        self.assertEqual(result, "测试输出")
        self.assertTrue(captured["url"].endswith("/chat/completions"))
        self.assertEqual(captured["headers"]["Authorization"], "Bearer sk-test")
        self.assertEqual(captured["payload"]["model"], "deepseek-chat")
        self.assertEqual(captured["payload"]["messages"][0]["content"], "提示词")

    def test_anthropic_payload_shape(self):
        config = provider.ProviderConfig.from_preset("anthropic")
        captured = {}

        def fake_post(url, headers, payload, timeout):
            captured.update(url=url, headers=headers, payload=payload)
            return {"content": [{"text": "第一段"}, {"text": "第二段"}]}

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant"}):
            with mock.patch.object(provider, "_post_json", fake_post):
                result = provider.complete(config, "提示词")

        self.assertEqual(result, "第一段第二段")
        self.assertTrue(captured["url"].endswith("/messages"))
        self.assertIn("x-api-key", captured["headers"])
        self.assertEqual(captured["headers"]["anthropic-version"], "2023-06-01")

    def test_client_error_not_retried(self):
        import urllib.error

        config = provider.ProviderConfig.from_preset("deepseek")
        config.max_retries = 3
        calls = []

        def fake_post(url, headers, payload, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(
                url, 401, "Unauthorized", {}, None
            )

        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-bad"}):
            with mock.patch.object(provider, "_post_json", fake_post):
                with self.assertRaises(RuntimeError) as ctx:
                    provider.complete(config, "提示词")

        self.assertEqual(len(calls), 1, "4xx 不应重试")
        self.assertIn("401", str(ctx.exception))

    def test_server_error_retried(self):
        import urllib.error

        config = provider.ProviderConfig.from_preset("deepseek")
        config.max_retries = 2
        calls = []

        def flaky_post(url, headers, payload, timeout):
            calls.append(1)
            if len(calls) < 2:
                raise urllib.error.HTTPError(url, 503, "Unavailable", {}, None)
            return {"choices": [{"message": {"content": "重试后成功"}}]}

        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            with mock.patch.object(provider, "_post_json", flaky_post):
                with mock.patch.object(provider.time, "sleep"):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = provider.complete(config, "提示词")

        self.assertEqual(result, "重试后成功")
        self.assertEqual(len(calls), 2)


class FormattingTests(unittest.TestCase):
    def test_pad_accounts_for_wide_characters(self):
        # 中文字符按 2 列宽计算
        self.assertEqual(provider._pad("中文", 10), "中文      ")
        self.assertEqual(provider._pad("ab", 5), "ab   ")

    def test_describe_includes_all_providers(self):
        text = provider.describe_providers()
        for name in provider.PROVIDER_PRESETS:
            self.assertIn(name, text)


class ExtractUsageTests(unittest.TestCase):
    """用量取不到时必须如实返回 available=False，绝不估算。"""

    def test_openai_shape(self):
        u = provider._extract_usage(
            {"usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        )
        self.assertTrue(u["available"])
        self.assertEqual(u["prompt_tokens"], 10)
        self.assertEqual(u["total_tokens"], 15)

    def test_anthropic_shape_is_normalised(self):
        u = provider._extract_usage(
            {"usage": {"input_tokens": 20, "output_tokens": 7}}
        )
        self.assertTrue(u["available"])
        self.assertEqual(u["prompt_tokens"], 20)
        self.assertEqual(u["completion_tokens"], 7)
        self.assertEqual(u["total_tokens"], 27)   # 未给 total 时自行相加

    def test_missing_usage_reports_unavailable(self):
        u = provider._extract_usage({"choices": []})
        self.assertFalse(u["available"])
        self.assertIn("usage", u["reason"])

    def test_unrecognised_usage_reports_unavailable(self):
        u = provider._extract_usage({"usage": {"something_else": 1}})
        self.assertFalse(u["available"])

    def test_none_result_is_safe(self):
        self.assertFalse(provider._extract_usage(None)["available"])


if __name__ == "__main__":
    unittest.main()
