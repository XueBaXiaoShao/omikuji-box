# おみくじ（omikuji-box）

每日固定结果的中文/日文抽签插件：同一 QQ 同一天结果一致，第二天自动刷新。
签纸采用和风 + 柚子社主题：柚子橙/柚叶绿配色、柚子社 logo、每日随机柚子社幸运角色，
以及带柚子社梗的幸运物。

## 功能

| 命令 | 说明 |
| --- | --- |
| `/omikuji` | 抽取今日御神签 |
| `/おみくじ` | 同上（日文别名） |
| `/御神籤` | 同上（日文别名） |
| `/omukuji` | `/omikuji` 的别名 |
| `/omikuji settings JP on\|off` | 切换个人显示语言（日文 / 中文） |
| `/omikuji reset @某人` / `/omikuji reset <QQ号>` | 重置指定用户今日御神签（仅管理员） |

- 总签运共 12 级：大吉 / 中吉 / 小吉 / 吉 / 半吉 / 末吉 / 末小吉 / 凶 / 小凶 / 半凶 / 末凶 / 大凶
- 概率：大吉 5% / 中吉 12% / 小吉 18% / 吉 20% / 半吉 12% / 末吉 9% / 末小吉 7% / 凶 8% / 小凶 4% / 半凶 3% / 末凶 1% / 大凶 1%
- 分项：恋爱、工作学业、财运、健康、人际（同样 12 级）
- 幸运物、幸运色、幸运方位、幸运数字
- 幸运物包含柚子社作品/角色梗（如「四季夏目的咖啡杯」「绫地宁宁的魔女帽」）
- 幸运物会按总签运从对应卡池抽取；「月望的白丝」仅大吉且默认 5% 概率出现，签纸会标记「稀有」
- 每日柚子社幸运角色：若当天抽过 `/yuzuwaifu`，优先显示该角色；否则从本地资料库随机抽取（带立绘）
- 若先抽 `/omikuji` 再抽 `/yuzuwaifu`，后者会沿用 omikuji 当天选中的柚子社角色；`/waifu` 等其他入口不受影响
- 同一用户同一天重复发送结果固定，跨群一致
- 支持中文 / 日文版本切换，切换语言不会改变当天的签运与抽取结果
- 不保存签文结果；为与 `/yuzuwaifu` 对齐，会记录当天选中的柚子社角色引用到
  `data/omikuji_yuzu.json`（reset 时清除）；reset 随机盐存
  `data/omikuji_state.json`，语言偏好存 `data/omikuji_settings.json`

## 配置

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `OMIKUJI_TIMEZONE` | `Asia/Shanghai` | 跨日时区 |
| `OMIKUJI_SEED_SALT` | `omikuji-box-v1` | 抽签种子盐，修改后全量结果变化 |
| `OMIKUJI_RARE_ITEM_CHANCE` | `0.05` | 稀有幸运物出现概率（0~1） |
| `OMIKUJI_ALLOWED_USERS` | 空 | 允许使用的 QQ 号，逗号分隔；留空时仅 `SUPERUSERS` 可用；填 `*` 全员开放 |

群级开关复用 `data/plugin_switches.json` 的 `omikuji_box` 键，
可用 `/shou switch omikuji_box on|off [群号]` 控制。

## 字体

- 中文字体：`omikuji_box/assets/fonts/omikuji-zh.(otf|ttf|ttc)`
- 日文字体：`omikuji_box/assets/fonts/omikuji-ja.(otf|ttf|ttc)`
- 未提供时回退到内置 `NotoSansSC-Regular.otf`；字体文件在每次渲染时读取，替换后无需重启。

## 测试

```bash
make test
```
