目标冻结

新增项目内 voice gateway，提供 AI 实时语音通话能力（WebSocket）。
客户端负责采集/播放；本项目负责会话编排、Omni/TTS、记忆流水线。
记忆策略固定为：
通话开始：注入“短期记忆 + 近 N 轮中期记忆”
通话中：不查长期记忆，短期窗口 + 动态压缩
通话结束：强制一次中期总结写入
一、代码结构规划（本项目）

voice_session.py (line 1)
POST /api/voice-session/token
WS /ws/voice-session
（可选）POST /api/voice-session/reload
config.py (line 1)
网关配置模型（采样率、超时、并发、记忆参数）
protocol.py (line 1)
事件 schema、错误码、可重连判定
auth.py (line 1)
short token 签发/校验
session.py (line 1)
单会话状态机与资源句柄
session_manager.py (line 1)
会话表、并发控制、清理与超时
audio_pipeline.py (line 1)
音频上行/下行处理、打断时清队列
omni_client.py (line 1)
Omni Realtime 接入（音频入、文本增量出）
tts_client.py (line 1)
TTS Realtime 接入（文本入、音频增量出）
memory_pipeline.py (line 1)
start/turn/end 记忆策略实现
metrics.py (line 1)
延迟、成功率、错误码统计
修改 main.py (line 1)
注册 voice_session 路由
修改 config.yaml (line 1)
增加 voice_gateway 配置段
修改 requirements.txt (line 1)
增补网关依赖（按最小化原则）
二、接口与协议（后端实现）

POST /api/voice-session/token
输入：chat_id/user_id/device_id/platform
输出：token/expires_in/session_id/ws_url
WS /ws/voice-session?token=...
文本事件：session.start、interrupt、session.end、ping/pong
二进制：audio.frame（v1 纯 PCM 裸流）
错误事件统一：error
字段：code/message/retryable/retry_after_ms
区分可重连与不可重连
三、会话状态机（后端）

状态：INIT -> AUTHED -> STARTED -> ACTIVE -> ENDING -> ENDED
异常态：FAILED、TIMEOUT
关键规则：
无 session.start 不接收音频帧
interrupt 立即触发：取消当前 AI 响应 + 清空下行播放队列
session.end 或断连：进入 finalize（保证记忆收尾）
空闲超时、最大通话时长超时自动结束
四、音频链路实现（后端）

上行固定：pcm16/le, 16k, mono, 20ms
处理链：WS binary -> audio_pipeline -> omni_client
下行链：omni text delta -> tts_client -> pcm frames -> WS binary
打断逻辑：
收到 interrupt 或检测用户开口事件
调 omni response.cancel
调 tts clear
丢弃未发完的音频帧
五、记忆流水线（按你定稿）

session.start
拉取短期记忆 + 近 N 轮中期记忆（默认 N=4）
拼接为会话初始上下文注入 Omni
通话中（turn）
维护短期窗口（最近 4~6 轮）
触发动态压缩条件：
轮数 > 6 或文本量 > 1500 字
生成“压缩摘要”回灌当前会话上下文（不写长期）
session.end（强制）
生成一次中期总结（含要点）
写入中期记忆
异常断线也执行兜底 finalize（幂等）
六、配置项设计（config.yaml）

voice_gateway.enabled
voice_gateway.ws.path
voice_gateway.auth.token_ttl_seconds
voice_gateway.call.max_duration_seconds
voice_gateway.call.idle_timeout_seconds
voice_gateway.audio.input_sample_rate/output_sample_rate/channels/frame_ms
voice_gateway.memory.mid_term_rounds_n
voice_gateway.memory.compress_trigger_rounds
voice_gateway.memory.compress_trigger_chars
voice_gateway.memory.summary_max_chars
voice_gateway.omni.*
voice_gateway.tts.*
voice_gateway.observability.trace_enabled
七、实施阶段（只后端）

P0：协议骨架 + token + WS 建连 + 会话状态机
P1：Omni/TTS 串联 + 实时音频上下行 + interrupt
P2：记忆流水线（start/turn/end）+ 异常兜底 finalize
P3：监控日志 + 错误码体系 + 压测与稳定性修复
八、测试计划（后端）

单元测试
protocol schema 校验
session 状态迁移
memory_pipeline 压缩触发与幂等 finalize
集成测试
mock 客户端推音频帧，验证下行音频返回
interrupt 生效时延
异常断开是否完成中期记忆写入
压测
单机并发会话数
30 分钟长会话内存稳定性
错误恢复成功率
九、验收标准（后端）

WS 建连成功率 ≥ 99%
首包音频延迟 P95 ≤ 1.8s（服务端侧统计）
interrupt 生效 P95 ≤ 600ms
异常断线 finalize 成功率 = 100%
通话中不触发长期记忆检索（日志可证明）