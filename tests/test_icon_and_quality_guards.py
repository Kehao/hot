import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.generate_curated_models as gm
from scripts.icon_resolver import resolve_icon


class IconAndQualityGuardTests(unittest.TestCase):
    def test_openrouter_model_uses_provider_icon_not_openrouter_favicon(self):
        item = {
            'name': 'Ling-2.6 1T (free)',
            'provider': 'InclusionAI',
            'url': 'https://openrouter.ai/inclusionai/ling-2.6-1t:free',
        }
        icon = resolve_icon(item, 'model')
        self.assertIn('inclusionai.com', icon)
        self.assertNotIn('openrouter.ai/favicon', icon)

    def test_github_project_uses_owner_avatar_not_github_favicon(self):
        item = {'name': 'Example', 'url': 'https://github.com/owner/repo'}
        self.assertEqual(resolve_icon(item, 'tool'), 'https://github.com/owner.png?size=128')

    def test_provider_uses_curated_provider_icon_not_url_fallback(self):
        item = {'id': 'baidu', 'name': 'Baidu Qianfan', 'url': 'https://cloud.baidu.com/product/wenxinworkshop'}
        icon = resolve_icon(item, 'provider')
        self.assertIn('yiyan.baidu.com', icon)
        self.assertNotIn('aihot.bt199.com/favicon', icon)

    def test_unresolved_item_does_not_hide_regression_with_site_favicon(self):
        item = {'name': 'Unknown Internal', 'url': 'https://example.invalid/no-brand'}
        self.assertNotIn('aihot.bt199.com/favicon', resolve_icon(item, 'model'))

    def test_generate_curated_models_has_ling_and_real_icons_from_fixture_without_mutating_repo_data(self):
        fixture = {
            'data': [
                {'id': 'openai/gpt-5.4', 'name': 'OpenAI: GPT-5.4', 'created': 100, 'context_length': 128000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'openai/gpt-5.5', 'name': 'OpenAI: GPT-5.5', 'created': 200, 'context_length': 256000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'openai/gpt-5.5-pro', 'name': 'OpenAI: GPT-5.5 Pro', 'created': 210, 'context_length': 256000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'openai/gpt-image-2', 'name': 'OpenAI: GPT Image 2', 'created': 220, 'context_length': 64000, 'architecture': {'input_modalities': ['text', 'image'], 'output_modalities': ['image']}},
                {'id': 'deepseek/deepseek-v3.2', 'name': 'DeepSeek: DeepSeek V3.2', 'created': 300, 'context_length': 128000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'deepseek/deepseek-v4-pro', 'name': 'DeepSeek: DeepSeek V4 Pro', 'created': 400, 'context_length': 128000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'qwen/qwen3.7-plus', 'name': 'Qwen: Qwen3.7 Plus', 'created': 500, 'context_length': 262144, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'xiaomi/mimo-32b', 'name': 'Xiaomi: MiMo 32B', 'created': 300, 'context_length': 128000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'xiaomi/mimo-v2-pro', 'name': 'Xiaomi: MiMo V2 Pro', 'created': 500, 'context_length': 128000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'minimax/minimax-m3', 'name': 'MiniMax: MiniMax M3', 'created': 400, 'context_length': 1000000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'z-ai/glm-5.2', 'name': 'Z.ai: GLM 5.2', 'created': 600, 'context_length': 1000000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'google/gemini-3.5-flash', 'name': 'Google: Gemini 3.5 Flash', 'created': 450, 'context_length': 1000000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
                {'id': 'anthropic/claude-opus-4.8', 'name': 'Anthropic: Claude Opus 4.8', 'created': 550, 'context_length': 1000000, 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            fixture_path = temp_dir / 'openrouter.json'
            fixture_path.write_text(json.dumps(fixture), encoding='utf-8')
            models_path = temp_dir / 'models.json'
            models_path.write_text(json.dumps([
                {'url': 'https://huggingface.co/Qwen/Qwen3-Coder-Next', 'author': 'Qwen', 'display_name': 'Qwen3-Coder-Next', 'created_at': '2026-01-30T00:00:00Z', 'likes': 1000, 'pipeline_tag': 'text-generation'},
                {'url': 'https://huggingface.co/moonshotai/Kimi-K2.6', 'author': 'moonshotai', 'display_name': 'Kimi-K2.6', 'created_at': '2026-04-14T00:00:00Z', 'likes': 900, 'pipeline_tag': 'text-generation'},
                {'url': 'https://huggingface.co/google/gemma-4-31B-it', 'author': 'google', 'display_name': 'gemma-4-31B-it', 'created_at': '2026-03-11T00:00:00Z', 'likes': 800, 'pipeline_tag': 'image-text-to-text'},
                {'url': 'https://huggingface.co/tencent/HY-Embodied-0.5', 'author': 'tencent', 'display_name': 'HY-Embodied-0.5', 'created_at': '2026-04-02T00:00:00Z', 'likes': 700, 'pipeline_tag': 'image-text-to-text'},
                {'url': 'https://huggingface.co/black-forest-labs/FLUX.1-dev', 'author': 'black-forest-labs', 'display_name': 'FLUX.1-dev', 'created_at': '2024-08-01T00:00:00Z', 'likes': 10000, 'pipeline_tag': 'text-to-image'},
                {'url': 'https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev', 'author': 'black-forest-labs', 'display_name': 'FLUX.1-Kontext-dev', 'created_at': '2025-05-01T00:00:00Z', 'likes': 5000, 'pipeline_tag': 'text-to-image'},
                {'url': 'https://huggingface.co/Lightricks/LTX-2.3', 'author': 'Lightricks', 'display_name': 'LTX-2.3', 'created_at': '2026-04-01T00:00:00Z', 'likes': 600, 'pipeline_tag': 'image-to-video'},
                {'url': 'https://huggingface.co/Qwen/Qwen2.5-72B-Instruct', 'author': 'Qwen', 'display_name': 'Qwen2.5-72B-Instruct', 'created_at': '2024-09-01T00:00:00Z', 'likes': 4000, 'pipeline_tag': 'text-generation'},
                {'url': 'https://huggingface.co/deepseek-ai/DeepSeek-V3', 'author': 'deepseek-ai', 'display_name': 'DeepSeek-V3', 'created_at': '2024-12-01T00:00:00Z', 'likes': 5000, 'pipeline_tag': 'text-generation'},
                {'url': 'https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct', 'author': 'meta-llama', 'display_name': 'Llama-3.1-8B-Instruct', 'created_at': '2024-07-01T00:00:00Z', 'likes': 4000, 'pipeline_tag': 'text-generation'},
                {'url': 'https://huggingface.co/openai/whisper-large-v3', 'author': 'openai', 'display_name': 'whisper-large-v3', 'created_at': '2023-11-01T00:00:00Z', 'likes': 3000, 'pipeline_tag': 'automatic-speech-recognition'},
                {'url': 'https://huggingface.co/Qwen/Qwen3.6-35B-A3B', 'author': 'Qwen', 'display_name': 'Qwen3.6-35B-A3B', 'created_at': '2026-03-01T00:00:00Z', 'likes': 600, 'pipeline_tag': 'text-generation'},
            ], ensure_ascii=False), encoding='utf-8')
            output_path = temp_dir / 'models_curated.json'
            with patch.dict('os.environ', {'OPENROUTER_MODELS_FIXTURE': str(fixture_path)}), \
                 patch.object(gm, 'MODELS_PATH', str(models_path)), \
                 patch.object(gm, 'OUTPUT_PATH', str(output_path)):
                gm.generate_curated_models()

            data = json.loads(output_path.read_text(encoding='utf-8'))

        names = [x['name'] for x in data['items']]
        self.assertTrue(any('GLM 5.2' in name for name in names))
        self.assertIn('DeepSeek V4 Pro', names)
        self.assertNotIn('DeepSeek V3.2', names)
        self.assertNotIn('MiMo 32B', names)
        bad_icons = [x for x in data['items'] if 'openrouter.ai/favicon' in x.get('icon_url', '') or 'github.com/favicon' in x.get('icon_url', '')]
        self.assertFalse(bad_icons)


if __name__ == '__main__':
    unittest.main()
