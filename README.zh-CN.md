# 微截（WeSnap）

[English](README.md) | **中文**

![CI](https://github.com/ChenyangZhao7/wesnap/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Windows 上自用的微信式截图工具：`Alt+A` 唤起、框选缩放、标注、贴图、滚动长截图，点「完成」自动存桌面并复制到剪贴板。

## 启动

- 双击桌面上的「微截」快捷方式，或双击 `wesnap\微截.vbs`。
- 程序常驻系统托盘，不弹控制台。首次启动如果 `Alt+A` 被占用，会自动打开设置窗口要求换键。
- 重新创建桌面快捷方式：`python tools\install_shortcut.py`
- 重新生成图标：`python tools\make_icon.py`

运行环境：已安装 Python 3.14 与 Pillow 13。本机已装好，无需重复安装。

## 用法

按 `Alt+A`（可在设置里改）进入截图：

- 拖拽框选；拖动选区四边/四角的 8 个手柄缩放；在选区内部拖动可整体移动；方向键微调 1px，`Shift+方向键` 10px。
- 工具栏：`[矩形] [椭圆] [箭头] [画笔] [文字] [马赛克] [撤销] | [长截图] [贴图] | [保存] [✓ 完成] [✕ 取消]`。
- 再点一次当前工具 = 退出标注模式，回到「拖动移动选区」。
- 文字：点选位置后输入，`Enter` 确认，`Esc` 取消；点界面其他任意位置也会自动提交；支持中文输入法。
- 「完成」：按设置保存到保存目录并复制到剪贴板；两个开关都关时改为弹「另存为」，避免丢图。`Enter`、双击选区、点「完成」都等价。
- 「保存」：另存为，不写剪贴板。
- 「贴图」：把截图钉在屏幕上；拖动移动，拖边缘缩放，滚轮缩放，右键菜单（复制 / 另存为 / 关闭），`Esc` 或双击关闭。
- 长截图：框选区域后点「长截图」，鼠标放在选区里滚动滚轮翻页，选区外的控制面板实时显示拼接预览；点「完成」保存并复制。选区外必须留得下控制面板，否则按钮置灰；有标注时需先撤销全部标注才能长截图；单张长图最高 30000px。
- `Esc` / 鼠标右键取消；`Enter` 完成；`Ctrl+Z` 撤销。

托盘：左键单击 = 截图；右键菜单 = 截图 / 设置… / 开机自启 / 退出。

## 文件位置

- 配置：`%APPDATA%\WeSnap\settings.json`
- 日志：`%APPDATA%\WeSnap\wesnap.log`（超过 1MB 滚动为 `wesnap.1.log`）
- 默认保存目录：桌面，文件名 `Screenshot_yyyyMMdd_HHmmss.png`，重名追加 `_2`、`_3`。

## 设置

托盘右键 → 设置…：录制新快捷键、选择保存目录、自动保存 / 自动复制 / 开机自启。快捷键冲突时会提示并保留窗口，不会假装成功。

## 为什么没有 exe

本机开启了 Smart App Control，会拦截所有未签名 exe。程序由已签名的 `pythonw.exe` 运行 Python 代码，所以交付形态是「程序文件夹 + 启动器/快捷方式」。关闭 Smart App Control 是不可逆的，也没有必要。

## 已知限制

- 跨显示器框选不支持：选区限定在按下热键时光标所在的那块屏幕。
- 长截图需要选区外有摆放控制面板的空间；单张长图最高 30000px；固定表头/侧边栏的页面可能出现重复条带或错位（所有滚轮拼接工具的通病）。
- 标注颜色/线宽固定为微信红 2px（数据模型已预留，后续可加调色板）。

## 开发

- 全部测试：`python -m unittest discover -s tests -v`（其中 4 项真实 GUI 事件测试默认跳过）
- GUI 事件级集成测试（会短暂显示全屏遮罩）：`$env:WESNAP_GUI_TESTS='1'; python -m unittest tests.test_screenshot_flow -v`
- 设计文档：`docs/superpowers/specs/2026-11-16-wesnap-design.md`
- 实现计划：`docs/superpowers/plans/2026-11-16-wesnap.md`
- 第三方依赖只有 Pillow；界面全部 Tk + ctypes 自绘。

## 协议

MIT
