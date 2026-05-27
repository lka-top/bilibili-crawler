# B站视频数据采集与分析工具

基于 Playwright + httpx 的 B站视频数据爬取与分析工具。

## 快速开始

```bash
# 安装依赖
uv sync

# 安装 Playwright 浏览器驱动
uv run playwright install chromium

# 运行项目
uv run python main.py
```

## 功能特性

- 多种登录方式（扫码登录 / Cookie 登录）
- 反检测浏览器自动化（Playwright + stealth.js）
- WBI 签名算法支持（B站 API 签名）
- 关键词搜索视频 & 按 BV 号获取视频详情
- 多格式数据存储（JSON / CSV）
- 词云和统计分析报告自动生成
- 代理池支持（可选）

## 核心依赖

- `playwright` - 浏览器自动化
- `httpx` - HTTP 客户端
- `pydantic` + `pydantic-settings` - 配置管理
- `loguru` - 日志系统
- `pandas` - 数据分析
- `jieba` + `wordcloud` - 分词 & 词云生成

## 命令行使用

```bash
# 交互模式（终端选择模式和参数）
python main.py

# 关键词搜索
python main.py -k "原神,星穹铁道"

# 按 BV 号获取视频详情
python main.py -b BV1xx411c7mD
python main.py -b "BV1xx,BV2yy,BV3zz"

# 查看完整帮助
python main.py --help
```

## 配置

复制 `.env` 并修改配置：

- `BILI_LOGIN_TYPE` — 登录方式：`cookie` 或 `qrcode`
- `BILI_COOKIE_STR` — Cookie 登录时填入完整的 Cookie 字符串
- `BILI_KEYWORDS` — 默认搜索关键词
- `BILI_MAX_VIDEO_COUNT` — 最大爬取数量
- `BILI_STORAGE_TYPE` — 存储格式：`json` 或 `csv`

## 项目结构

```
bilibili-crawler/
├── config/          # 配置模块（settings + B站 API 配置）
├── core/            # 浏览器管理模块
├── login/           # 登录认证模块（扫码 + Cookie）
├── client/          # B站 API 客户端（WBI 签名）
├── crawler/         # 爬虫调度模块
├── models/          # 数据模型（BilibiliVideo）
├── store/           # 数据存储模块
├── analysis/        # 分析报告生成（词云 + 统计）
├── proxy/           # 代理池模块
├── tools/           # 工具函数（WBI 签名算法）
├── main.py          # 主程序入口
└── test_quick.py    # 快速测试脚本
```

## 运行结果

运行成功后会在 `output/` 目录下生成：
- `<关键词>_results/<关键词>.json` — 采集的视频数据
- `<关键词>_results/<关键词>.md` — 数据分析报告
- `<关键词>_results/<关键词>.png` — 标题词云图片

## 参考

- [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
- 请遵守 B站的使用条款和法律法规
