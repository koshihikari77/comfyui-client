"""
インラインプレースホルダー ({a | b | c}) のテスト

- expand_inline_placeholders() 単体テスト
- PromptResolverV2 統合テスト（expand / sample / 混在）
"""
import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from random import Random

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.resolver.placeholder import expand_inline_placeholders, PlaceholderSubstitutor
from core.resolver.context import ResolverContext
from core.prompt_resolver_v2 import PromptResolverV2


# ---------------------------------------------------------------------------
# 単体テスト: expand_inline_placeholders()
# ---------------------------------------------------------------------------

class TestExpandInlinePlaceholders:
    """expand_inline_placeholders の前処理ロジックをテスト"""

    def test_basic_inline(self):
        """基本: パイプ区切りの候補が抽出される"""
        tpl = "foo, {from side | pov | from above}, bar"
        result, ph, counter = expand_inline_placeholders(tpl, {})
        assert counter == 1
        assert "_inline_0" in ph
        assert ph["_inline_0"] == ["from side", "pov", "from above"]
        # expand モード（:r なし）
        assert "{_inline_0}" in result
        assert ":r" not in result

    def test_sample_mode(self):
        """:r 付きで sample モードになる"""
        tpl = "{a | b | c:r}"
        result, ph, counter = expand_inline_placeholders(tpl, {})
        assert ph["_inline_0"] == ["a", "b", "c"]
        assert "{_inline_0:r}" in result

    def test_empty_option_trailing_pipe(self):
        """末尾パイプで空選択肢が追加される"""
        tpl = "{tag_a | tag_b | }"
        result, ph, _ = expand_inline_placeholders(tpl, {})
        assert ph["_inline_0"] == ["tag_a", "tag_b", ""]

    def test_empty_option_with_sample(self):
        """空選択肢 + :r"""
        tpl = "{tag_a | tag_b | :r}"
        result, ph, _ = expand_inline_placeholders(tpl, {})
        assert ph["_inline_0"] == ["tag_a", "tag_b", ""]
        assert "{_inline_0:r}" in result

    def test_multiple_inline(self):
        """複数インラインが独立して処理される"""
        tpl = "{a | b}, {c | d}"
        result, ph, counter = expand_inline_placeholders(tpl, {})
        assert counter == 2
        assert ph["_inline_0"] == ["a", "b"]
        assert ph["_inline_1"] == ["c", "d"]
        assert "{_inline_0}" in result
        assert "{_inline_1}" in result

    def test_no_inline(self):
        """パイプを含まない {} は変換しない"""
        tpl = "{shot}, plain text"
        result, ph, counter = expand_inline_placeholders(tpl, {})
        assert counter == 0
        assert result == tpl
        assert "shot" not in ph

    def test_external_placeholders_preserved(self):
        """既存の外部プレースホルダーが維持される"""
        existing = {"shot": ["closeup", "medium"]}
        tpl = "{shot}, {a | b}"
        result, ph, _ = expand_inline_placeholders(tpl, existing)
        assert ph["shot"] == ["closeup", "medium"]
        assert ph["_inline_0"] == ["a", "b"]
        # {shot} はそのまま残る
        assert "{shot}" in result

    def test_counter_start(self):
        """counter_start で連番を制御できる"""
        tpl = "{x | y}"
        result, ph, counter = expand_inline_placeholders(tpl, {}, counter_start=5)
        assert "_inline_5" in ph
        assert counter == 6

    def test_nested_braces_not_matched(self):
        """ネストした {} はマッチしない（[^{}] で防止）"""
        tpl = "{{a | b} | c}"
        # 内側の {a | b} にはマッチするが、外側のネスト { にはマッチしない
        result, ph, counter = expand_inline_placeholders(tpl, {})
        # {a | b} がマッチして置換される
        assert counter == 1

    def test_whitespace_handling(self):
        """前後のスペースがトリムされる"""
        tpl = "{ a |  b  | c }"
        result, ph, _ = expand_inline_placeholders(tpl, {})
        assert ph["_inline_0"] == ["a", "b", "c"]

    def test_single_pipe(self):
        """2 択"""
        tpl = "{yes | no}"
        result, ph, _ = expand_inline_placeholders(tpl, {})
        assert ph["_inline_0"] == ["yes", "no"]


# ---------------------------------------------------------------------------
# 統合テスト: PromptResolverV2 との連携
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_prompts_dir():
    """最小限のプロンプトディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()
    prompts_dir = Path(temp_dir) / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "presets").mkdir()
    (prompts_dir / "wildcards").mkdir()
    yield str(prompts_dir)
    shutil.rmtree(temp_dir)


def _make_resolver(prompts_dir, placeholders=None, seed=42):
    config = {
        "seed": seed,
        "locale": ",",
        "strict_level": "warn",
        "placeholders": placeholders or {},
    }
    return PromptResolverV2(prompts_dir, config)


class TestInlinePlaceholderIntegration:
    """PromptResolverV2 でのインラインプレースホルダー統合テスト"""

    def test_resolve_inline_expand_basic(self, temp_prompts_dir):
        """expand（デフォルト）: resolve_nth で直積展開"""
        resolver = _make_resolver(temp_prompts_dir)
        tpl = "girl, {from side | pov | from above}"

        results = [resolver.resolve_nth(tpl, i) for i in range(3)]
        # 3 通りのそれぞれが含まれる
        result_set = set(results)
        assert "girl, from side" in result_set
        assert "girl, pov" in result_set
        assert "girl, from above" in result_set

    def test_resolve_inline_sample(self, temp_prompts_dir):
        """sample (:r): resolve() でランダム 1 つ"""
        resolver = _make_resolver(temp_prompts_dir)
        tpl = "girl, {from side | pov | from above:r}"

        result = resolver.resolve(tpl)
        assert result in ["girl, from side", "girl, pov", "girl, from above"]

    def test_resolve_inline_with_external(self, temp_prompts_dir):
        """外部参照と共存"""
        resolver = _make_resolver(
            temp_prompts_dir,
            placeholders={"shot": ["closeup", "medium"]},
        )
        tpl = "{shot}, {a | b}"

        # shot=2 x inline=2 = 4 通り
        results = set(resolver.resolve_nth(tpl, i) for i in range(4))
        assert len(results) == 4
        expected = {
            "closeup, a", "closeup, b",
            "medium, a", "medium, b",
        }
        assert results == expected

    def test_resolve_inline_multiple_expand(self, temp_prompts_dir):
        """複数インラインの直積: 2 x 3 = 6"""
        resolver = _make_resolver(temp_prompts_dir)
        tpl = "{a | b}, {x | y | z}"

        results = set(resolver.resolve_nth(tpl, i) for i in range(6))
        assert len(results) == 6

    def test_resolve_inline_empty_option(self, temp_prompts_dir):
        """空選択肢が正しく動作する"""
        resolver = _make_resolver(temp_prompts_dir)
        tpl = "girl, {hand up | }"

        results = set(resolver.resolve_nth(tpl, i) for i in range(2))
        # 空選択肢の場合は "girl, " が返る（末尾スペースありだが TagFilter がトリムする）
        assert any("hand up" in r for r in results)
        # 空選択肢でも何らかの結果がある
        assert len(results) == 2

    def test_resolve_inline_cycle(self, temp_prompts_dir):
        """cycle: n が候補数を超えると巡回する"""
        resolver = _make_resolver(temp_prompts_dir)
        tpl = "{a | b}"

        r0 = resolver.resolve_nth(tpl, 0)
        r2 = resolver.resolve_nth(tpl, 2)
        # cycle=True なので 2 % 2 = 0 と同じ結果
        assert r0 == r2

    def test_context_not_polluted(self, temp_prompts_dir):
        """インライン処理後に context.placeholders が汚染されない"""
        resolver = _make_resolver(
            temp_prompts_dir,
            placeholders={"shot": ["closeup"]},
        )
        original_keys = set(resolver.context.placeholders.keys())

        resolver.resolve("girl, {a | b | c}")

        # _inline_X が残っていないこと
        assert set(resolver.context.placeholders.keys()) == original_keys
