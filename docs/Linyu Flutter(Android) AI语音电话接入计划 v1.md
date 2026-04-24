Linyu Flutter(Android) AI语音电话接入计划 v1

1) 目标与范围
在聊天页新增“AI语音电话”按钮，进入 AI 实时语音会话。
与现有电话功能并存，不影响原通话入口。
首版实现：建连、实时上行录音、实时下行播音、挂断、基础重连、会话记忆同步。
2) 代码改造清单（按文件）
logic.dart (line 1)

新增状态：
isAiCalling
aiCallState（idle/connecting/listening/speaking/reconnecting/ended/failed）
isAiMuted、isAiSpeakerOn
新增方法：
startAiCall()
endAiCall()
onAiInterrupt()
onAiWsDisconnected()
保留现有 isRecording，不要改坏原语音消息逻辑。
index.dart (line 1)

在不破坏原录音发送的前提下，新增“流式录音模式”：
onPcmFrame(Uint8List frame) 回调
onRecordStart/onRecordStop
基于 record 包输出实时帧（16k/mono/pcm16）。
index.dart (line 1)

继续用于“语音消息回放”。
AI 实时播放建议单独模块，不强行复用该组件（避免影响现有语音消息功能）。
voice.dart (line 1)

保持原有语音消息渲染，不改业务行为。
新增模块（建议）

ai_call_ws_service.dart
ai_call_audio_player.dart
ai_call_event.dart
ai_call_controller.dart
ai_call_sheet.dart
职责：协议收发、状态机、音频上下行、UI状态展示。
3) UI 交互改造
在聊天输入区/工具栏新增按钮：AI语音电话
点击后弹出 AI 通话浮层（底部或全屏）：
状态文案：连接中 / 你在说话 / AI在说话 / 重连中
按钮：挂断、静音、免提
原电话按钮保持不变（走原流程）。
4) 音频与传输规范（Android首版）
上行（客户端→网关）：
PCM16、16kHz、mono，20ms一帧（约640字节）
下行（网关→客户端）建议二选一：
方案A（推荐）：下发 PCM16，客户端用实时PCM播放器模块播放（低延迟）
方案B：下发 AAC/Opus 分片，客户端解码播放（实现更复杂）
VAD/打断：
用户开口时发 interrupt，服务端停止当前AI播报并切换聆听。
5) 客户端-网关协议（建议最小集）
建连：wss://<host>/ws/voice-session?token=<short_token>
事件：
session.start
audio.frame（二进制）
interrupt
session.end
ping/pong
回包：
session.ready
audio.frame（二进制）
transcript.user.delta/final（可选）
transcript.ai.delta/final（可选）
error
6) Android 侧配置
AndroidManifest.xml (line 1) 增加/确认：
RECORD_AUDIO
INTERNET
MODIFY_AUDIO_SETTINGS
（可选）FOREGROUND_SERVICE（若需后台持续通话）
音频焦点与回声控制：启用 audio_session 管理（建议）。
7) 实施里程碑
P0（2~4天）：按钮、建连、上行录音、下行播放、挂断
P1（2~3天）：重连、打断、状态机完善、错误处理
P2（2天）：记忆事件（start/turn/end）、埋点指标、体验细化
8) 验收标准
建连成功率（4G/WiFi）≥ 95%
首次出声延迟 P95 ≤ 2.0s
打断生效 P95 ≤ 700ms
连续 15 分钟通话无崩溃、无明显卡顿
原语音消息与原电话功能不回归