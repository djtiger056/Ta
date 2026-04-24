Linyu Server 实时音视频通话技术分析报告

  一、项目概述

  该项目是一个基于 WebRTC 的实时音视频通话信令服务器，采用 Spring Boot + Netty 架构实现。核心功能包括 WebSocket       
  长连接管理、 WebRTC
  信令转发、通话邀请与控制等。项目仅负责信令服务器功能，音视频媒体流的采集、编解码、传输由客户端 WebRTC API
  实现。

  二、技术架构

  核心通信框架：项目使用 Netty 4.x 作为 WebSocket 服务器基础，监听 9100 端口提供实时通信服务。Netty
  的事件驱动模型能够高效处理大量并发连接，每个连接通过 Channel 对象表示，用户 ID 与 Channel 的映射关系存储在
  ConcurrentHashMap 中实现线程安全的在线状态管理。

  信令传输机制：所有 WebRTC 信令（Offer、Answer、Candidate、Invite、Accept、Hangup）通过 HTTP POST 请求发送到
  /v1/api/video/ 端点，由 VideoService 处理后，通过 WebSocket
  实时转发给目标用户。这种设计将信令的控制逻辑与传输层分离，便于扩展和维护。

  用户状态管理：用户上线时通过 Token 验证建立 WebSocket 连接，系统更新 Redis
  缓存和数据库中的在线状态；离线时清理相关映射并更新状态。系统配置 30
  秒心跳检测，超时未响应的连接将被自动断开，确保在线状态准确性。

  三、核心组件说明

  NettyWebSocketServer 是整个实时通信的入口类，负责初始化 Netty 服务器。该类配置了双 EventLoopGroup：bossGroup        
  负责处理连接请求，workerGroup 负责处理具体的 IO 操作。服务器配置了 HTTP 编解码器、ChunkedWriteHandler
  支持大文件传输、HttpObjectAggregator 聚合 HTTP 消息，以及 WebSocketServerProtocolHandler 处理 WebSocket 协议。      

  NettyWebSocketServerHandler 处理 WebSocket 连接生命周期事件。handlerAdded 在 Channel
  添加时执行初始化，channelRead 处理接收到的文本消息，userEventTriggered 处理心跳超时事件。当检测到 30
  秒读空闲时，触发用户下线逻辑，清理在线状态并关闭连接。

  VideoService 封装了视频通话的核心业务逻辑。offer 方法处理发起方的 SDP Offer 消息，answer 方法处理接收方的 SDP       
  Answer 消息，candidate 方法转发 ICE 候选信息，invite 方法处理通话邀请并标记是否为纯语音通话，accept
  方法确认接受通话，hangup 方法处理挂断请求。所有方法最终调用 WebSocketService 将消息推送给目标用户。

  四、信令通信流程

   ┌────────────────────────────────────────────────────────────────────┐
   │                      WebRTC 信令交互流程                            │
   └────────────────────────────────────────────────────────────────────┘

   用户A                          信令服务器                        用户B
     │                               │                               │
     │───── 1. Invite 请求 ─────────>│                               │
     │                               │───── WebSocket 推送 ────────> │
     │                               │                               │
     │                               │                               │
     │<───── 2. WebSocket 通知 ─────│<───── 3. Accept 请求 ─────── │
     │                               │                               │
     │───── 4. WebSocket 推送 ────>│───── 5. Accept 响应 ────────> │
     │                               │                               │
     │                               │                               │
     │───── 6. Offer 请求 ─────────>│                               │
     │                               │───── WebSocket 推送 ────────> │
     │                               │                               │
     │<───── 7. WebSocket 通知 ─────│<───── 8. Answer 请求 ─────── │
     │                               │                               │
     │───── 9. WebSocket 推送 ────>│───── 10. Answer 响应 ───────>│
     │                               │                               │
     │                               │                               │
     │<───── 11. Candidate 交换 ────────────────────────────────────>│
     │<───── (双向 ICE 候选信息) ────────────────────────────────────>│
     │                               │                               │
     │                               │                               │
     │───── 12. Hangup 请求 ───────>│                               │
     │                               │───── WebSocket 推送 ────────> │

  第一步，用户 A 通过 HTTP POST 发送邀请请求到 /v1/api/video/invite，服务器验证双方好友关系后，通过 WebSocket
  将邀请信息推送给用户 B。第二步，用户 B 选择接受通话，发送 HTTP POST 到 /v1/api/video/accept，服务器通知用户 A       
  通话已建立。第三步，用户 A 生成 SDP Offer 并发送到 /v1/api/video/offer，服务器转发给用户 B。第四步，用户 B
  生成 SDP Answer 并发送到 /v1/api/video/answer，服务器转发给用户 A。第五步，双方开始交换 ICE Candidate
  信息，通过 /v1/api/video/candidate 端点发送，服务器负责转发。第六步，任一方可发送挂断请求到
  /v1/api/video/hangup，服务器通知对方通话结束。

  五、数据结构定义

  WsContent 是 WebSocket 消息的统一封装结构，包含 type 字段标识消息类型（msg、notify、video）和 content
  字段承载具体消息内容。这种设计将不同类型的消息统一处理，便于扩展新的消息类型。

  视频通话相关 VO 类：
   - OfferVo：包含目标用户 ID、发起方 ID、SDP 描述信息（type 为 video 或 audio）、是否为纯语音标识
   - AnswerVo：包含目标用户 ID、发起方 ID、SDP 描述信息
   - CandidateVo：包含目标用户 ID、发起方 ID、ICE 候选信息（candidate、sdpMid、sdpMLineIndex、usernameFragment）      
   - InviteVo：包含目标用户 ID、发起方 ID、是否为纯语音通话标识
   - AcceptVo：包含目标用户 ID、发起方 ID
   - HangupVo：包含目标用户 ID、发起方 ID

  在线用户映射：
   - Online_User：ConcurrentHashMap<String userId, Channel>，通过用户 ID 快速查找对应的 Channel
   - Online_Channel：ConcurrentHashMap<Channel, String>，通过 Channel 反查用户 ID

  六、配置参数汇总

  WebSocket 服务器配置：
   - 监听端口：9100
   - 心跳超时：30 秒（IdleStateReaderTimeout）
   - Worker 线程数：CPU 核心数（NettyRuntime.availableProcessors）
   - HTTP 消息聚合缓冲区：8192 字节

  消息类型常量（WsContentType）：
   - video 类型：用于视频通话信令推送
   - msg 类型：用于普通消息推送
   - notify 类型：用于通知消息推送

  语音识别配置：
   - 语音转文字模型路径：/model/faster-whisper-small/
   - 语音识别 API 地址：http://123.207.210.163:8000/v1/audio/transcriptions

  七、集成建议

  客户端实现要求：如需在其他项目中集成实时音视频通话，客户端需实现完整的 WebRTC API，包括 MediaStream API
  获取本地音视频流，RTCPeerConnection 建立对等连接，SdpObserver 处理 SDP 交换，IceCandidate
  收集和交换网络候选信息。WebSocket 连接需在请求头携带 x-token 参数进行身份验证，心跳间隔建议 30
  秒以内以维持连接活跃。

  服务端部署要求：建议部署 STUN/TURN 服务器（如 coturn）以支持复杂网络环境下的 NAT 穿透。项目支持使用 Docker
  Compose 一键部署，包含 MySQL、Redis、RocketMQ 等依赖服务。生产环境需配置域名 SSL 证书，确保 WebSocket 使用 WSS      
  安全协议传输。

✦ 安全增强建议：当前系统未对通话请求进行频次限制和通话状态持久化，建议增加通话请求限流策略防止恶意调用，设计通话      
  记录数据库表存储通话日志、通话时长、参与者信息等数据，实现服务器端通话状态管理确保双方状态同步。