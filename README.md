# ok-roko

`ok-roko` 是一个基于 `ok-script` 开发的《洛克王国：世界》Windows 自动化项目，当前主要实现的是自动刷花相关流程。

项目仓库：
`https://github.com/aimer-rhythm/ok-roko`

## 当前状态

当前主任务为 `自动刷花`。

执行流程：

`自动召唤前置检测 -> 自动召唤（按需）-> 自动鞠躬`

其中：

- 每次自动鞠躬前，都会先调用一次自动召唤模块。
- 自动召唤模块会先用 OCR 识别界面中是否存在 `F2`、`F3` 等快捷键文字，用来判断当前是否处于游戏主界面。
- 如果当前不是主界面，则跳过自动召唤逻辑。
- 如果当前画面里没有识别到 1 号位精灵区域，也会跳过自动召唤逻辑。
- 如果识别到 1 号位精灵区域，则会继续检测其是否已召唤。
- 已召唤时跳过自动召唤，未召唤时按 `1 -> 左键 -> 2 -> 左键 -> 3 -> 左键 -> 4 -> 左键 -> 5 -> 左键 -> 6 -> 左键` 执行自动召唤。
- 自动鞠躬模块按 `Tab -> 2 -> ESC` 循环执行。

## 1 号位精灵召唤检测

当前识别逻辑不是直接比较整张游戏截图，而是：

1. 使用参考图中左侧的 `数字 1 圆圈` 作为定位锚点。
2. 在整张游戏画面左上区域搜索该锚点，先定位 1 号位精灵卡片区域。
3. 根据参考图中右上角图标的相对位置，截取 1 号位精灵卡片右上角的小区域。
4. 将该小区域分别与：
   - [`assets/unsummoned.png`](/D:/Project/ok-roko/assets/unsummoned.png)
   - [`assets/summoned-icon.png`](/D:/Project/ok-roko/assets/summoned-icon.png)
   进行匹配。
5. 根据已召唤图标分数判断当前状态。

相关代码：

- [`AutoFlowerTask.py`](/D:/Project/ok-roko/src/tasks/AutoFlowerTask.py)
- [`AutoSummonModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoSummonModule.py)
- [`AutoBowModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoBowModule.py)

## 调试输出

当使用 `main_debug.py` 运行时，每次进行 1 号位精灵状态检测都会输出最新调试图到：

`D:\Project\ok-roko\.tmp\auto-summon-slot-one-debug\latest`

常见文件说明：

- `frame.png`: 原始整帧截图。
- `frame-boxes.png`: 在整帧截图上画出了搜索框、定位框、图标匹配框。
- `search-region.png`: 用于查找 1 号位精灵区域的左上搜索区域。
- `slot-region.png`: 识别出的 1 号位精灵完整区域。
- `locator-template.png`: 用来定位左侧 `数字 1 圆圈` 的模板。
- `locator-matched-patch.png`: 当前帧中匹配到的锚点区域。
- `icon-patch.png`: 从 1 号位精灵右上角截出来用于判断召唤状态的小图。
- `unsummoned-icon-template.png`: 未召唤图标参考模板。
- `summoned-icon-template.png`: 已召唤图标参考模板。
- `unsummoned-matched-patch.png`: 当前帧中与未召唤模板对应的匹配结果。
- `summoned-matched-patch.png`: 当前帧中与已召唤模板对应的匹配结果。
- `metadata.json`: 本次识别的分数、坐标和模板来源。

如果识别失败，还会额外生成带时间戳的调试目录，便于回溯单次问题。

## 当前任务列表

项目当前注册的单次任务在 [`src/config.py`](/D:/Project/ok-roko/src/config.py) 中定义：

1. `测试任务`
2. `自动刷花`
3. `DiagnosisTask`

说明：

- `测试任务` 是模板遗留的示例任务，主要用于 OCR、点击和自定义 Tab 联调。
- `自动刷花` 是当前实际业务任务。
- `调整游戏时间模块` 已有实现，但在 `AutoFlowerTask` 中默认关闭，不会实际执行。

## 自定义界面

项目保留了一个示例自定义 Tab：

- [`MyTab.py`](/D:/Project/ok-roko/src/ui/MyTab.py)

这个页面当前仍是示例内容，按钮点击后会调用 `测试任务`。

## 运行环境

- Windows
- Python `3.12`
- 目标游戏进程：`NRC-Win64-Shipping.exe`
- 推荐分辨率比例：`16:9`
- 最低支持分辨率：`1280 x 720`

项目默认使用：

- OCR：`onnxocr`
- 截图：`WGC`, `BitBlt_RenderFull`
- 交互：`PostMessage`, `Pynput`, `Genshin`, `PyDirect`, `ForegroundPostMessage`

## 从源码运行

先安装依赖：

```powershell
pip install -r requirements.txt --upgrade
```

运行正式模式：

```powershell
python main.py
```

运行调试模式：

```powershell
python main_debug.py
```

直接启动自动刷花并在任务完成后退出：

```powershell
python main_debug.py -t 2 -e
```

说明：

- `-t 2` 对应当前任务列表中的第 2 个任务，也就是 `自动刷花`。
- `-e` 表示任务结束后自动退出。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m unittest tests.TestMain
```

当前已覆盖的测试主要包括：

- 自动鞠躬循环顺序
- 自动召唤按键与文本输入回退
- 主界面 OCR 判断
- 1 号位精灵区域缺失时跳过
- 1 号位精灵已召唤 / 未召唤识别
- 调整游戏时间模块的关键流程

## 打包

打包配置文件：

- [`pyappify.yml`](/D:/Project/ok-roko/pyappify.yml)

当前正式包配置：

- 项目名：`ok-roko`
- Release 仓库地址：`https://github.com/aimer-rhythm/ok-roko`

GitHub Actions 工作流：

- [`.github/workflows/build.yml`](/D:/Project/ok-roko/.github/workflows/build.yml)

## 目录说明

```text
assets/                    模板图、参考图、识别素材
configs/                   运行时配置
icons/                     图标资源
i18n/                      国际化资源
logs/                      日志输出
ok_tasks/                  ok-script 任务相关目录
screenshots/               截图输出目录
src/config.py              项目主配置
src/tasks/                 任务实现
src/tasks/auto_flower/     自动刷花相关模块
src/ui/                    自定义界面
tests/                     单元测试
main.py                    正式入口
main_debug.py              调试入口
pyappify.yml               打包配置
README.md                  项目说明
```

## 主要文件

- [`src/config.py`](/D:/Project/ok-roko/src/config.py): 项目配置、任务注册、窗口标题、OCR 与截图配置。
- [`src/tasks/AutoFlowerTask.py`](/D:/Project/ok-roko/src/tasks/AutoFlowerTask.py): 自动刷花总任务入口。
- [`src/tasks/auto_flower/AutoSummonModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoSummonModule.py): 自动召唤、主界面判断、1 号位精灵已召唤检测、调试图输出。
- [`src/tasks/auto_flower/AutoBowModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoBowModule.py): 自动鞠躬循环逻辑。
- [`src/tasks/auto_flower/AutoAdjustTimeModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoAdjustTimeModule.py): 调整游戏时间模块，当前默认未启用。
- [`tests/TestMain.py`](/D:/Project/ok-roko/tests/TestMain.py): 当前测试用例。

## 说明

这个仓库已经从 `ok-script boilerplate` 模板切换为当前 `ok-roko` 项目，但仍保留少量模板示例代码，后续可以继续清理：

- `测试任务`
- `MyTab`
- 部分示例配置项

当前如果要继续迭代业务功能，建议优先围绕 `src/tasks/auto_flower/` 目录展开。
