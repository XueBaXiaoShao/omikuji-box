"""おみくじ：中文日式抽签与柚子社主题和风签纸。"""

from nonebot.plugin import PluginMetadata

from . import commands  # noqa: F401

__plugin_meta__ = PluginMetadata(
    name="おみくじ",
    description=(
        "每日固定结果的中文/日文抽签，生成柚子社主题和风签纸；"
        "含每日柚子社幸运角色与柚子社梗幸运物，支持 JP 语言切换。"
    ),
    usage="/omikuji、/omikuji settings JP on|off、/omikuji reset @某人|<QQ号>（管理员）",
    type="application",
    homepage="",
    supported_adapters={"~onebot.v11"},
)
