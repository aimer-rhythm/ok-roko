# ok-roko

`ok-roko` 是一个基于 `ok-script` 开发的《洛克王国：世界》Windows 自动化项目，当前主要实现的是自动刷花相关流程。

项目仓库：
`https://github.com/aimer-rhythm/ok-roko`

## 当前状态

当前主任务为 `自动刷花`。

执行流程：

`自动召唤前置检测 -> 1-6 槽位召唤状态识别 -> 按需补召 -> 全量复检补召 -> 自动鞠躬`

其中：

- 每次自动鞠躬前，都会先调用一次自动召唤模块。
- 自动召唤模块会先用 OCR 识别界面中是否存在 `F2`、`F3` 等快捷键文字，用来判断当前是否处于游戏主界面。
- 如果当前不是主界面，则跳过自动召唤逻辑。
- 进入主界面后，会基于 `assets/result.json` 中 1-6 号槽位的标注框，对 6 个槽位逐个识别当前是否已召唤。
- 如果 6 个槽位都已召唤，则直接跳过自动召唤模块。
- 如果存在未召唤槽位或识别异常槽位，则只对这些目标槽位执行 `数字键 -> 左键` 的定向召唤。
- 首轮召唤完成后，还会再次全量复检 6 个槽位；若仍有未召唤或识别异常槽位，会继续补召直到全部识别为已召唤。
- 自动鞠躬模块按 `Tab -> 2 -> ESC` 循环执行；如果 `2` 的按键发送失败，会在指定交互模式下回退为文本输入。

## 1-6 槽位精灵召唤检测

当前识别逻辑不是直接比较整张游戏截图，而是：

1. 启动时读取 [`assets/result.json`](/D:/Project/ok-roko/assets/result.json) 中 1-6 号槽位的已召唤标注框。
2. 按当前分辨率把标注框缩放到实时截图上，得到每个槽位对应的目标区域。
3. 以目标区域为中心扩出一圈搜索边距，截取每个槽位的小范围图像作为图标搜索区。
4. 在该搜索区内查找对应槽位的已召唤特征：
   - `first_summoned`
   - `second_summoned`
   - `third_summoned`
   - `fourth_summoned`
   - `five_summoned`
   - `six_summoned`
5. 已召唤特征匹配分数大于等于 `0.80` 时判定为 `summoned`，否则判定为 `unsummoned`。
6. 单个槽位召唤后会立即复检；若仍未召唤，或复检时发生识别异常，则等待后重试，直到该槽位识别为已召唤。

相关代码：

- [`AutoFlowerTask.py`](/D:/Project/ok-roko/src/tasks/AutoFlowerTask.py)
- [`AutoSummonModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoSummonModule.py)
- [`AutoBowModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoBowModule.py)

## 调试输出

当使用 `main_debug.py` 运行，且某个槽位状态识别发生异常时，会额外输出一份调试材料到：

`D:\Project\ok-roko\.tmp\auto-summon-slot-debug\<时间戳目录>`

常见文件说明：

- `frame.png`: 原始整帧截图。
- `frame-boxes.png`: 在整帧截图上画出了槽位区域框、图标搜索框、匹配框。
- `search-region.png`: 当前槽位对应的搜索区域。
- `slot-region.png`: 当前槽位的标注框截图。
- `locator-template.png`: 当前槽位的区域模板。
- `locator-mask.png`: 当前槽位的模板遮罩。
- `locator-matched-patch.png`: 当前帧中对应槽位的匹配区域。
- `icon-patch.png`: 当前槽位用于查找已召唤特征的小范围图像。
- `summoned-matched-patch.png`: 当前帧中已召唤特征的实际匹配结果。
- `metadata.json`: 本次识别的槽位编号、分数、状态、坐标、异常原因与模板来源。

说明：

- 调试材料按时间戳单独建目录，不会覆盖历史记录。
- 正常识别通过时不会自动生成这一批诊断文件。

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

## 内存优化与排查

项目针对长时间挂机场景进行了深度内存优化，目前的优化措施包括：

1.  **降低分配压力**：将 `AutoBowModule` 的模板轮询间隔从 0.1s 提升至 **0.5s**，显著降低了高频图像拷贝带来的内存分配速率。
2.  **精准 OCR 扫描**：为 `Tab` 文字和主界面快捷键识别引入了**局部区域扫描 (ROI)**。通过指定 `box` 限制，避开了代价昂贵且易导致泄露的全屏 OCR 路径。
3.  **主动垃圾回收**：在核心任务循环（如自动召唤补召、自动鞠躬轮询）的关键节点引入了 `gc.collect()`，确保大型图像对象和 OCR 中间件能被及时释放。
4.  **精简图像流转**：重构了 `MyBaseTask` 的底层取帧逻辑，消除了 BGRA 转换过程中的冗余全屏拷贝。
5.  **增强缓存稳定性**：优化了匹配阈值，提高了模板缓存命中率，进一步减少了对 OCR 引擎的调用频率。

**观察建议：**

- **基准内存**：开启 OCR 后，由于 OpenVINO 模型加载及显存映射，RSS 通常会稳定在 **380MB - 1.2GB** 之间（取决于是否启用 GPU/OpenCL 加速），这是正常现象。
- **稳定性判断**：重点观察日志中的 `delta` 值。在优化后，长时间运行下的 `delta` 应趋于 **+0.0MB** 或在极小范围内波动，不再出现步进式增长。
- **排查工具**：
    - 直接用 `main_debug.py` 运行。`debug=True` 时会自动开启详细的内存埋点。
    - 也可以手动设置环境变量 `OK_ROKO_MEMORY_PROBE=1`。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m unittest tests.TestMain
```

当前已覆盖的测试主要包括：

- 自动鞠躬循环顺序
- Tab 未就绪时的重试逻辑
- 自动召唤按键与文本输入回退
- 主界面 OCR 判断
- 1-6 号槽位已召唤 / 未召唤识别
- 未召唤槽位的定向召唤与全量补召
- 召唤后复检失败时的重试与修复
- 调整游戏时间模块的关键流程

## 打包

打包配置文件：

- [`pyappify.yml`](/D:/Project/ok-roko/pyappify.yml)

当前正式包配置：

- 项目名：`ok-roko`
- Release 仓库地址：`https://github.com/aimer-rhythm/ok-roko`

GitHub Actions 工作流：

- [`.github/workflows/build.yml`](/D:/Project/ok-roko/.github/workflows/build.yml)

当前发布触发方式：

- 推送普通提交只会更新代码，不会自动打包 Release。
- 推送符合 `v*` 格式的 Git tag 时，会触发 `Build` 工作流。
- 工作流会在 `windows-latest` 上安装依赖、执行 `tests/` 下的单元测试、调用 `pyappify-action` 打包，并将 `pyappify_dist/*` 上传到对应 GitHub Release。
- 也可以手动使用 `workflow_dispatch` 触发构建，但自动发布 Release 仍依赖 tag 引用。

## 目录说明

```text
assets/                    模板图、参考图、识别素材
configs/                   运行时配置
docs/                      开发文档与 ok-script 相关说明
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
- [`src/tasks/auto_flower/AutoSummonModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoSummonModule.py): 自动召唤、主界面判断、1-6 号槽位状态识别、按需补召、复检修复、调试图输出。
- [`src/tasks/auto_flower/AutoBowModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoBowModule.py): 自动鞠躬循环逻辑。
- [`src/tasks/auto_flower/AutoAdjustTimeModule.py`](/D:/Project/ok-roko/src/tasks/auto_flower/AutoAdjustTimeModule.py): 调整游戏时间模块，当前默认未启用。
- [`tests/TestMain.py`](/D:/Project/ok-roko/tests/TestMain.py): 当前测试用例。

## 说明

这个仓库已经从 `ok-script boilerplate` 模板切换为当前 `ok-roko` 项目，但仍保留少量模板示例代码，后续可以继续清理：

- `测试任务`
- `MyTab`
- 部分示例配置项

后续开发请优先阅读并遵循 [`docs/`](/D:/Project/ok-roko/docs) 目录下的文档，当前已包含：

- [`ok-script API文档.md`](/D:/Project/ok-roko/docs/ok-script%20API文档.md)
- [`ok-script 进阶使用指南.md`](/D:/Project/ok-roko/docs/ok-script%20进阶使用指南.md)

在继续迭代业务功能时，代码实现建议优先围绕 `src/tasks/auto_flower/` 目录展开，并以 `docs/` 目录中的文档约定为准。
