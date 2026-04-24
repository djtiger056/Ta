# LFBot 项目文档

## 项目概述

LFBot 是一个 AI 聊天陪伴机器人系统，具有记忆功能、语音合成能力和多平台适配能力。该项目采用前后端分离架构，后端使用 FastAPI + Python，前端使用 React + TypeScript + Ant Design。

### 核心功能
- AI 对话聊天（支持多种 LLM 提供商：OpenAI、Claude、SiliconFlow、DeepSeek）
- 智能记忆系统（短期、中期、长期记忆）
- TTS 语音合成（支持启航AI提供商）
- 图像生成系统（支持火山引擎API和豆包AI网站自动化）
- 文本清洗和分段处理
- 多平台适配（QQ、控制台、Web）
- Web 管理界面（聊天、设置、历史记录、记忆管理、TTS配置、图像生成配置）
- 实时流式回复
- 会话管理

### 技术栈

**后端技术：**
- FastAPI - Web 框架
- SQLAlchemy + AsyncPG - 数据库 ORM
- ChromaDB - 向量数据库（长期记忆）
- Sentence Transformers - 文本嵌入
- WebSocket - 实时通信
- Pydantic - 数据验证
- aiohttp - 异步 HTTP 客户端
- Loguru - 日志系统

**前端技术：**
- React 19 - UI 框架
- TypeScript - 类型安全
- Ant Design 6 - UI 组件库
- React Router 7 - 路由管理
- Axios - HTTP 客户端
- Vite 7 - 构建工具
- React Markdown - Markdown 渲染
- React Syntax Highlighter - 代码高亮
- Emotion - CSS-in-JS 样式库

**AI/记忆技术：**
- OpenAI/Claude/SiliconFlow/DeepSeek API - LLM 提供商
- ChromaDB - 向量存储
- RAG（检索增强生成）- 记忆检索

**图像生成技术：**
- 火山引擎 Seedream API - 付费图像生成


**TTS 技术：**
- 启航AI TTS - 主要语音合成提供商
- 文本清洗 - 自动过滤不适合语音朗读的内容

## 项目结构

```
E:\MyProject\LFbot\
├───backend/                 # 后端代码
│   ├───adapters/           # 平台适配器（QQ、控制台）
│   ├───api/                # API 路由（WebSocket、记忆管理、TTS）
│   ├───core/               # 核心业务逻辑（Bot、消息、会话）
│   ├───memory/             # 记忆系统（管理器、模型、向量存储）
│   ├───providers/          # LLM 提供商（OpenAI、Claude）
│   ├───tts/                # TTS 语音合成系统
│   │   └───providers/      # TTS 提供商实现
│   ├───image_gen/          # 图像生成系统（新增）
│   │   ├───providers/      # 图像生成提供商
│   │   │   ├───volcengine.py  # 火山引擎API提供商
│   │   │   └───doubao.py      # 豆包AI网站自动化提供商
│   │   ├───config.py       # 图像生成配置
│   │   └───manager.py      # 图像生成管理器
│   ├───utils/              # 工具类（文本分割器等）
│   ├───config.py           # 配置管理
│   ├───logger.py           # 日志系统
│   └───main.py             # FastAPI 应用入口
├───frontend/               # 前端代码
│   ├───src/
│   │   ├───components/     # React 组件
│   │   ├───pages/          # 页面组件
│   │   ├───services/       # API 服务
│   │   ├───styles/         # 样式文件
│   │   └───types/          # TypeScript 类型定义
│   ├───dist/               # 构建输出
│   └───package.json        # 前端依赖
├───data/                   # 数据存储
│   ├───chroma/             # 向量数据库
│   └───memory/             # 记忆数据文件
├───logs/                   # 日志文件
├───venv/                   # Python 虚拟环境
├───config.yaml             # 主配置文件
├───run.py                  # 启动脚本
├───requirements.txt        # Python 依赖
├───package.json            # 项目根依赖
└───start.bat               # Windows 启动脚本
```

## 构建和运行

### 环境准备

#### ⚠️ 虚拟环境要求
**强烈建议使用虚拟环境**运行本项目，以避免依赖冲突和环境污染。项目已提供自动化设置脚本。

1. **Python 环境（后端）：**
   
   **推荐方式：使用自动化脚本**
   ```bash
   # 运行setup.bat自动化设置（Windows）
   setup.bat
   # 脚本会自动：检查Python → 创建虚拟环境 → 安装依赖 → 提供使用指引
   ```
   
   **备用方式：手动设置**
   ```bash
   # 创建虚拟环境
   python -m venv venv
   
   # 激活虚拟环境（Windows）
   venv\Scripts\activate
   
   # 安装依赖
   pip install -r requirements.txt
   

   ```

2. **Node.js 环境（前端）：**
   ```bash
   cd frontend
   npm install
   ```

#### 虚拟环境管理工具
- **`setup.bat`**: 自动化环境设置脚本，简化初始配置
- **`run.py`**: 智能启动脚本，自动检测虚拟环境状态并提供指引
- **`.gitignore`**: 已配置忽略虚拟环境文件，避免提交到版本控制

### 启动方式

**方式一：使用启动脚本（推荐）**
```bash
# Windows
start.bat

# 或者直接运行
python run.py
```

**方式二：分别启动前后端**

1. **启动后端：**
   ```bash
   python run.py
   # 或
   python backend/main.py
   ```

2. **启动前端：**
   ```bash
   cd frontend
   npm run dev
   ```

**方式三：控制台模式**
```bash
python run.py console
```

### 默认访问地址
- 后端 API: http://localhost:8000
- 前端界面: http://localhost:3000
- API 文档: http://localhost:8000/docs

## 快速使用指南

### 图像生成功能使用

1. **配置图像生成**:
   - 访问前端设置页面 (http://localhost:3000)
   - 在"图像生成设置"中选择提供商：
     - **火山引擎API**: 需要API密钥，生成速度快


2. **QQ中使用**:
   - 发送包含触发词的消息：
     - "画一只可爱的小猫"
     - "生成图片：美丽的风景"
     - "帮我生图，主题是星空"
   - 系统会自动生成并发送图片

3. **测试功能**:
   - 在前端设置页面点击"测试API连接"
   - 输入测试提示词，点击"生成测试"
   - 查看生成结果和预览图片

### 配置示例



# 使用火山引擎API（付费）
image_generation:
  enabled: true
  provider: volcengine
  volcengine:
    api_key: "your-api-key-here"
    model: "doubao-seedream-4-5-251128"
```

## 配置说明

### 主配置文件 (config.yaml)

主要配置项：

```yaml
# 适配器配置
adapters:
  console:
    enabled: true
  qq:
    enabled: true
    ws_host: 127.0.0.1
    ws_port: 3001
    access_token: ''
    need_at: true

# 数据库配置
database:
  url: sqlite+aiosqlite:///./data/lfbot.db

# LLM 配置
llm:
  provider: siliconflow
  model: deepseek-ai/DeepSeek-V3
  api_base: https://api.siliconflow.cn/v1
  api_key: your-api-key
  temperature: 0.7
  max_tokens: 2000

# 记忆系统配置
memory:
  short_term_enabled: true
  mid_term_enabled: true
  long_term_enabled: true
  embedding_model: paraphrase-multilingual-MiniLM-L12-v2
  rag_top_k: 3
  rag_score_threshold: 0.5
  short_term_max_rounds: 50
  summary_interval: 10
  summary_max_length: 500
  max_summaries: 10
  max_long_term_memories: 1000

# 服务器配置
server:
  host: 0.0.0.0
  port: 8000
  debug: true

# TTS 配置
tts:
  enabled: true
  probability: 1.0
  provider: qihang
  qihang:
    api_base: https://api.qhaigc.net/v1
    api_key: your-api-key
    model: qhai-tts
    voice: 柔情萝莉
  segment_config:
    enabled: true
    strategy: last
    max_segments: 1
    send_timing: async
    delay_range: [0.5, 2.0]
    min_segment_length: 5
    max_segment_length: 100
    interval_step: 2
  text_cleaning:
    enabled: false
    remove_emoji: true
    remove_kaomoji: true
    remove_action_text: true
    remove_brackets_content: true
    remove_markdown: true
    max_length: 500

# 图像生成配置
image_generation:
  enabled: true
  provider: doubao  # 可选: volcengine, doubao
  volcengine:
    api_base: https://ark.cn-beijing.volces.com/api/v3
    api_key: your-api-key
    model: doubao-seedream-4-5-251128
    default_size: 2K
    watermark: false
  doubao:
    headless: true  # 是否无头模式
    timeout: 120    # 超时时间（秒）
    download_dir: "./data/temp_images"  # 图片下载目录
    max_retries: 3  # 最大重试次数
    wait_timeout: 30  # 等待元素超时（秒）
    website_url: "https://www.doubao.com/chat/create-image"
  trigger_keywords:
    - 画
    - 生成图片
    - 生图
    - 绘制
  generating_message: 🎨 正在为你生成图片，请稍候...
  error_message: 😢 图片生成失败：{error}
  success_message: ✨ 图片已生成完成！

# 系统提示词
system_prompt: |
  你需要扮演一名角色：余念安
  ...
```

## 开发约定

### 代码风格
- **Python**: 遵循 PEP 8，使用 type hints
- **TypeScript**: 使用严格模式，遵循 React 最佳实践
- **文件命名**: 使用 snake_case（Python）和 PascalCase（React 组件）

### API 设计
- 使用 FastAPI 的异步模式
- 统一的错误处理和日志记录
- RESTful API 设计原则
- WebSocket 用于实时通信

### 记忆系统架构
- **短期记忆**: 当前会话的消息历史（最大50轮对话）
- **中期记忆**: 会话摘要，每10轮生成一次摘要（最多10个摘要）
- **长期记忆**: 重要信息提取，使用向量存储（最多1000条记忆）

### 测试
```bash
# 后端测试
pytest

# 前端测试
cd frontend
npm run lint
```

## 核心模块说明

### Bot 核心类 (`backend/core/bot.py`)
- 处理用户消息的核心逻辑
- 整合记忆系统和 LLM 提供商
- 支持流式和非流式回复

### 记忆管理器 (`backend/memory/manager.py`)
- 三层记忆系统管理
- 自动摘要生成
- 重要信息提取和存储

### 平台适配器 (`backend/adapters/`)
- QQ 适配器：通过 WebSocket 连接 QQ 机器人
- 控制台适配器：命令行交互界面

### LLM 提供商 (`backend/providers/`)
- **base.py**: LLM 提供商基础接口
- **openai_provider.py**: OpenAI 兼容提供商（支持 OpenAI、SiliconFlow、DeepSeek）
- **claude_provider.py**: Claude 提供商
- **__init__.py**: 提供商注册和工厂函数

### 前端页面
- **ChatPage**: 主聊天界面
- **SettingsPage**: 系统设置（包含图像生成配置）
- **HistoryPage**: 聊天历史记录
- **MemorySettingsPage**: 记忆系统设置
- **MemoryViewPage**: 记忆数据查看
- **TTSConfigPage**: TTS 语音合成配置

### TTS 语音合成系统

#### 后端 TTS 模块 (`backend/tts/`)
- **base.py**: TTS 提供商基础接口
- **manager.py**: TTS 管理器，处理语音合成逻辑
- **text_cleaner.py**: 文本清洗工具，过滤不适合语音朗读的内容
- **providers/**: TTS 提供商实现
  - **qihang.py**: 启航AI TTS 提供商

#### TTS 功能特性
- **多提供商支持**: 启航AI（已实现）
- **智能文本清洗**: 自动移除 emoji、颜文字、动作描述、Markdown 等
- **分段处理**: 支持长文本分段合成和发送
- **概率触发**: 可配置触发概率，避免过度语音回复
- **音色选择**: 支持多种音色选择和切换

### 图像生成系统

#### 后端图像生成模块 (`backend/image_gen/`)
- **config.py**: 图像生成配置模型
- **manager.py**: 图像生成管理器，处理配置和触发逻辑
- **providers/**: 图像生成提供商实现
  - **volcengine.py**: 火山引擎API提供商（付费）


#### 图像生成功能特性
- **多提供商支持**: 火山引擎API（付费）
- **智能触发检测**: 自动检测消息中的触发关键词
- **网页自动化**: 使用Playwright自动访问网站、输入提示词、点击生成、下载图片
- **配置灵活**: 支持热切换提供商，前端可视化配置
- **错误处理**: 完善的异常处理和重试机制

#### 工作流程
1. QQ用户发送包含触发词的消息（如"画一只猫"）
2. Bot检测到触发词，提取提示词
3. 根据配置选择提供商：
   - **火山引擎模式**: 调用API生成图片
4. 将生成的图片发送给QQ用户

### 工具模块 (`backend/utils/`)
- **text_splitter.py**: 文本分割工具，用于处理长文本

## 部署注意事项

1. **环境变量**: 确保正确设置 API 密钥等敏感信息
2. **数据库**: 生产环境建议使用 PostgreSQL 而非 SQLite
3. **端口配置**: 确保前后端端口不冲突（前端默认3000，后端8000）
4. **日志管理**: 定期清理日志文件
5. **数据备份**: 定期备份 ChromaDB 向量数据库和记忆数据

## 故障排除

### 常见问题
1. **端口占用**: 检查 8000 和 3000 端口是否被占用
2. **API 连接失败**: 检查网络连接和 API 密钥配置
3. **记忆系统异常**: 检查 ChromaDB 数据目录权限
4. **前端构建失败**: 确保 Node.js 版本兼容（推荐使用最新 LTS 版本）
5. **TTS 不工作**: 检查 TTS 提供商配置和 API 密钥
6. **图像生成失败**:
   - **火山引擎模式**: 检查 API 密钥和网络连接
   - **豆包AI模式**: 运行 `playwright install chromium` 安装浏览器
   - 检查网站是否可访问，页面结构是否变化
   - 查看日志文件获取详细错误信息

### 日志位置
- 应用日志: `logs/lfbot_YYYY-MM-DD.log`
- 数据库文件: `data/chroma/chroma.sqlite3`
- 记忆数据: `data/memory/`

## 扩展开发

### 添加新的 LLM 提供商
1. 在 `backend/providers/` 创建新的提供商类
2. 继承 `BaseLLMProvider` 接口
3. 在 `providers/__init__.py` 的 `PROVIDERS` 字典中注册

### 添加新的平台适配器
1. 在 `backend/adapters/` 创建适配器类
2. 继承 `BaseAdapter` 接口
3. 在 `main.py` 中注册适配器

### 添加新的 TTS 提供商
1. 在 `backend/tts/providers/` 创建新的提供商类
2. 继承 TTS 基础接口
3. 在 `tts/providers/__init__.py` 中导出

### 添加新的图像生成提供商
1. 在 `backend/image_gen/providers/` 创建新的提供商类
2. 实现 `generate()` 和 `test_connection()` 方法
3. 在 `providers/__init__.py` 中导出
4. 更新 `config.py` 添加相应的配置模型
5. 更新前端配置页面支持新提供商

### 扩展记忆功能
1. 修改 `backend/memory/models.py` 添加新数据模型
2. 在 `manager.py` 中实现相应逻辑
3. 更新前端界面支持新功能

## 版本信息

- **React**: 19.2.3
- **TypeScript**: 5.9.3
- **Ant Design**: 6.1.1
- **Vite**: 7.3.0
- **FastAPI**: 0.109.0
- **ChromaDB**: 0.4.22
- **Sentence Transformers**: 2.3.1
- **Playwright**: 1.41.0（用于网页自动化）