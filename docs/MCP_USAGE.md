# MCP 扩展使用说明

## 功能概览
- 内置 MCP 管理器，支持列出、安装、执行插件。
- 自带时钟插件 `clock`，提供 `now` 工具，自动向对话注入当前本地/UTC 时间，解决“没有时间观念”问题。
- 插件配置持久化在 `data/mcp_plugins.json`，重启后自动加载。

## API
- 列出插件：`GET /api/mcp/plugins`
- 安装插件：`POST /api/mcp/plugins/install`
  - Body 示例：
    ```json
    {
      "name": "my_plugin",
      "pip_spec": "my-mcp-plugin==0.1.0",
      "module": "my_plugin.entrypoint",
      "class_name": "Plugin",
      "description": "自定义示例",
      "auto_context": false,
      "meta": {}
    }
    ```
- 执行插件工具：`POST /api/mcp/plugins/{plugin_name}/execute`
  - Body 示例（调用内置时钟）：`{"tool": "now", "params": {"include_timezone": true}}`

## 对话自动上下文
- Bot 每次聊天会从开启 `auto_context` 的插件收集上下文，并写入系统提示。
- 内置 `clock` 插件默认开启 `auto_context`，无需手动调用即可获得当前时间语境。
- 内置 `bing_cn_search` 插件默认开启 `auto_context`，当用户消息中出现“搜索/查一下/最新进展”等表达时，会自动联网检索并注入搜索摘要。

## 必应中文搜索插件（`bing_cn_search`）
- 工具 1：`bing_search`
  - 参数：`query`（必填）、`count`（可选，默认 10，最大 50）、`offset`（可选，默认 0）
  - 作用：返回标题、链接、摘要，以及格式化文本
- 工具 2：`crawl_webpage`
  - 参数：`url`（必填）、`max_chars`（可选，默认 8000）
  - 作用：抓取网页正文文本，自动过滤部分黑名单站点

调用示例：

```bash
curl -X POST http://localhost:8000/api/mcp/plugins/bing_cn_search/execute \
  -H "Content-Type: application/json" \
  -d "{\"tool\":\"bing_search\",\"params\":{\"query\":\"人工智能 最新进展\",\"count\":5}}"
```

```bash
curl -X POST http://localhost:8000/api/mcp/plugins/bing_cn_search/execute \
  -H "Content-Type: application/json" \
  -d "{\"tool\":\"crawl_webpage\",\"params\":{\"url\":\"https://example.com/article\"}}"
```

## 时钟插件时间不准怎么办？
- 云端主机时区可能与预期不同，可在环境变量或配置中指定：`CLOCK_TIMEZONE=UTC+08:00` 或在 `config.yaml` 添加 `clock: { timezone: "Asia/Shanghai" }`。
- 支持 IANA 时区名（如 `Asia/Shanghai`）或固定偏移（如 `UTC+08:00`）；未配置时默认使用主机系统时间。

## 安装自定义插件说明
1) 确保 pip 包可用，且暴露模块与类（默认类名 `Plugin`，需实现 `list_tools` 和 `run_tool`，可选 `auto_context_block`）。
2) 调用安装接口注册：见上方 `POST /api/mcp/plugins/install` 示例。
3) 调用执行接口运行工具：`/api/mcp/plugins/{plugin}/execute`。

## 路径与重启
- 插件注册表：`data/mcp_plugins.json`
- 如遇安装/导入失败，修正后可删除对应条目或清空该文件，再重启后端。
