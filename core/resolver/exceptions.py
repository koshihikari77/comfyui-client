"""
PromptResolver V2 例外クラス階層

設計書10.3に基づく例外クラス定義
"""


class ResolverError(Exception):
    """PromptResolver関連の基底例外クラス"""
    pass


class ParseError(ResolverError):
    """テンプレート解析エラー"""
    def __init__(self, message: str, template: str = "", position: int = -1):
        super().__init__(message)
        self.template = template
        self.position = position


class PresetNotFoundError(ResolverError):
    """プリセット未定義エラー"""
    def __init__(self, message: str, preset_key: str = ""):
        super().__init__(message)
        self.preset_key = preset_key


class PlaceholderError(ResolverError):
    """プレースホルダー関連エラー"""
    def __init__(self, message: str, placeholder_name: str = ""):
        super().__init__(message)
        self.placeholder_name = placeholder_name


class WildcardError(ResolverError):
    """ワイルドカード関連エラー"""
    def __init__(self, message: str, wildcard_key: str = ""):
        super().__init__(message)
        self.wildcard_key = wildcard_key


class RecursionLimitError(ResolverError):
    """再帰深度制限エラー"""
    def __init__(self, message: str, depth: int = 0):
        super().__init__(message)
        self.depth = depth