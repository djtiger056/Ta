林语聊天服务器项目详细分析

  一、项目架构概览

  技术栈

  ┌───────────┬────────────────┬────────────────────┐
  │ 组件      │ 技术           │ 版本               │
  ├───────────┼────────────────┼────────────────────┤
  │ 后端框架  │ Spring Boot    │ 2.6.7              │
  │ Java版本  │ Java           │ 1.8                │
  │ 数据库    │ MySQL          │ 8.0.37             │
  │ 缓存      │ Redis          │ 5.0.14.1           │
  │ 对象存储  │ MinIO          │ RELEASE.2024-05-10 │
  │ 消息队列  │ RocketMQ       │ 5.3.0              │
  │ WebSocket │ Netty          │ 4.1.108.Final      │
  │ ORM框架   │ MyBatis Plus   │ 3.5.1              │
  │ JWT认证   │ JWT            │ 0.9.0              │
  │ 语音识别  │ Faster-Whisper │ -                  │
  └───────────┴────────────────┴────────────────────┘

  端口配置

  ┌──────┬───────────────────────┐
  │ 端口 │ 服务                  │
  ├──────┼───────────────────────┤
  │ 9200 │ HTTP REST API         │
  │ 9100 │ WebSocket服务 (Netty) │
  │ 3306 │ MySQL数据库           │
  │ 6379 │ Redis                 │
  │ 9000 │ MinIO                 │
  │ 9876 │ RocketMQ NameServer   │
  └──────┴───────────────────────┘

  ---

  二、核心API接口汇总

  1. 登录认证模块 (LoginController)
   GET  /v1/api/login/public-key      # 获取RSA公钥
   POST /v1/api/login                 # 账号密码登录
   POST /v1/api/login/qr              # 二维码登录

  2. 用户模块 (UserController)
   POST /v1/api/user/search           # 搜索用户
   GET  /v1/api/user/unread           # 获取用户未读数
   POST /v1/api/user/email/verify     # 发送邮箱验证码
   POST /v1/api/user/register         # 用户注册
   POST /v1/api/user/forget           # 忘记密码
   GET  /v1/api/user/info             # 获取当前用户信息
   POST /v1/api/user/update           # 修改用户信息
   POST /v1/api/user/update/password  # 修改密码
   POST /v1/api/user/upload/portrait  # 上传头像
   GET  /v1/api/user/get/file         # 获取文件
   GET  /v1/api/user/get/img          # 获取图片

  3. 好友模块 (FriendController)
   GET  /v1/api/friend/list                      # 获取好友列表
   GET  /v1/api/friend/list/flat                 # 获取扁平化好友列表
   GET  /v1/api/friend/is/friend                 # 判断是否是好友
   GET  /v1/api/friend/list/flat/unread          # 获取带未读数的好友列表
   GET  /v1/api/friend/details/{friendId}        # 获取好友详情
   POST /v1/api/friend/search                    # 搜索好友
   POST /v1/api/friend/agree                     # 同意好友请求
   POST /v1/api/friend/agree/id                  # 根据ID同意好友请求
   POST /v1/api/friend/reject                    # 拒绝好友请求
   POST /v1/api/friend/add/qr                    # 扫码添加好友
   POST /v1/api/friend/set/remark                # 设置好友备注
   POST /v1/api/friend/set/group                 # 设置好友分组
   POST /v1/api/friend/delete                    # 删除好友
   POST /v1/api/friend/carefor                   # 特别关心
   POST /v1/api/friend/uncarefor                 # 取消特别关心
   POST /v1/api/friend/set-chat-background       # 设置聊天背景

  4. 消息模块 (MessageController)
   POST /v1/api/message/send                      # 发送消息给用户
   POST /v1/api/message/retraction                # 撤回消息
   POST /v1/api/message/reedit                    # 重新编辑消息
   POST /v1/api/message/record                    # 获取聊天记录
   POST /v1/api/message/record/desc               # 获取聊天记录(降序)
   POST /v1/api/message/send/file                 # 发送文件
   POST /v1/api/message/send/file/form            # 发送文件(表单)
   POST /v1/api/message/send/Img                  # 发送图片
   GET  /v1/api/message/get/file                  # 获取文件
   GET  /v1/api/message/get/media                 # 获取媒体(预览)
   GET  /v1/api/message/voice/to/text             # 语音消息转文字
   GET  /v1/api/message/voice/to/text/from        # 语音消息转文字(群聊)

  5. 群组模块 (ChatGroupController)
   GET  /v1/api/chat-group/list         # 获取聊天群列表
   POST /v1/api/chat-group/create       # 创建聊天群
   POST /v1/api/chat-group/update       # 更新群信息
   POST /v1/api/chat-group/update/name  # 更新群名称
   POST /v1/api/chat-group/invite       # 邀请成员
   POST /v1/api/chat-group/quit         # 退出群聊
   POST /v1/api/chat-group/kick         # 踢出群聊
   POST /v1/api/chat-group/dissolve     # 解散群聊
   POST /v1/api/chat-group/transfer     # 转让群聊
   POST /v1/api/chat-group/details      # 获取群详情
   POST /v1/api/chat-group/upload/portrait  # 上传群头像

  6. 聊天列表模块 (ChatListController)
   GET  /v1/api/chat-list/list          # 获取聊天列表
   POST /v1/api/chat-list/search        # 搜索好友或群组
   POST /v1/api/chat-list/create        # 创建聊天会话
   POST /v1/api/chat-list/delete        # 删除会话
   POST /v1/api/chat-list/top           # 设置置顶会话
   GET  /v1/api/chat-list/read/{targetId}  # 消息已读
   GET  /v1/api/chat-list/read/all      # 全部已读
   POST /v1/api/chat-list/detail        # 获取详细信息

  7. 说说模块
  说说主接口 (`TalkController`):
   POST /v1/api/talk/list         # 获取说说列表
   POST /v1/api/talk/details      # 获取说说详情
   POST /v1/api/talk/create       # 创建说说
   POST /v1/api/talk/upload/img   # 上传说说图片
   POST /v1/api/talk/delete       # 删除说说

  评论接口 (`TalkCommentController`):
   POST /v1/api/talk-comment/create   # 创建评论
   POST /v1/api/talk-comment/list     # 获取评论列表
   POST /v1/api/talk-comment/delete   # 删除评论

  点赞接口 (`TalkLikeController`):
   POST /v1/api/talk-like/create   # 点赞
   POST /v1/api/talk-like/list     # 获取点赞列表
   POST /v1/api/talk-like/delete   # 取消点赞

  8. 通知模块 (NotifyController)
   GET  /v1/api/notify/friend/list   # 好友通知列表
   POST /v1/api/notify/friend/apply  # 好友申请通知
   POST /v1/api/notify/read          # 通知已读
   GET  /v1/api/notify/system/list   # 系统通知列表

  9. 视频通话模块 (VideoController)
   POST /v1/api/video/offer    # 发送WebRTC Offer
   POST /v1/api/video/answer   # 发送WebRTC Answer
   POST /v1/api/video/candidate  # 发送ICE Candidate
   POST /v1/api/video/hangup   # 挂断
   POST /v1/api/video/invite   # 邀请通话
   POST /v1/api/video/accept   # 接受通话

  ---

  三、核心数据表设计

  1. 用户表 (user)

  ┌───────────┬──────────────┬────────────┐
  │ 字段      │ 类型         │ 说明       │
  ├───────────┼──────────────┼────────────┤
  │ id        │ varchar(64)  │ 主键       │
  │ account   │ varchar(64)  │ 用户账号   │
  │ name      │ varchar(200) │ 用户名     │
  │ portrait  │ text         │ 头像       │
  │ password  │ varchar(200) │ 密码(加密) │
  │ sex       │ varchar(64)  │ 性别       │
  │ birthday  │ timestamp(3) │ 生日       │
  │ signature │ text         │ 签名       │
  │ phone     │ varchar(64)  │ 手机号     │
  │ email     │ varchar(200) │ 邮箱       │
  │ role      │ varchar(64)  │ 用户角色   │
  │ is_online │ bit          │ 是否在线   │
  └───────────┴──────────────┴────────────┘

  2. 消息表 (message)

  ┌─────────────┬──────────────┬────────────────┐
  │ 字段        │ 类型         │ 说明           │
  ├─────────────┼──────────────┼────────────────┤
  │ id          │ varchar(64)  │ 主键           │
  │ from_id     │ varchar(64)  │ 发送方ID       │
  │ to_id       │ varchar(64)  │ 接收方ID       │
  │ type        │ varchar(64)  │ 消息类型       │
  │ msg_content │ text         │ 消息内容(JSON) │
  │ status      │ varchar(500) │ 消息状态       │
  │ source      │ varchar(64)  │ 消息源         │
  └─────────────┴──────────────┴────────────────┘

  消息内容类型:
   - text - 文本
   - img - 图片
   - file - 文件
   - voice - 语音
   - retraction - 撤回
   - call - 通话
   - system - 系统
   - quit - 退出群

  3. 好友表 (friend)

  ┌────────────┬─────────────┬──────────────┐
  │ 字段       │ 类型        │ 说明         │
  ├────────────┼─────────────┼──────────────┤
  │ id         │ varchar(64) │ 主键         │
  │ user_id    │ varchar(64) │ 用户ID       │
  │ friend_id  │ varchar(64) │ 好友ID       │
  │ remark     │ varchar(64) │ 备注         │
  │ group_id   │ varchar(64) │ 分组ID       │
  │ is_back    │ bit         │ 是否拉黑     │
  │ is_concern │ bit         │ 是否特别关心 │
  └────────────┴─────────────┴──────────────┘

  4. 群组表 (chat_group)

  ┌─────────────────┬─────────────┬────────────┐
  │ 字段            │ 类型        │ 说明       │
  ├─────────────────┼─────────────┼────────────┤
  │ id              │ varchar(64) │ 主键       │
  │ user_id         │ varchar(64) │ 创建用户ID │
  │ owner_user_id     │ varchar(64) │ 群主ID     │
  │ portrait        │ text        │ 群头像     │
  │ name            │ varchar(64) │ 群名称     │
  │ member_num      │ int         │ 成员数     │
  │ chat_group_number │ varchar(64) │ 群号       │
  └─────────────────┴─────────────┴────────────┘

  5. 聊天列表表 (chat_list)

  ┌────────────────┬─────────────┬──────────────┐
  │ 字段           │ 类型        │ 说明         │
  ├────────────────┼─────────────┼──────────────┤
  │ id             │ varchar(64) │ 主键         │
  │ user_id        │ varchar(64) │ 用户ID       │
  │ from_id        │ varchar(64) │ 会话目标ID   │
  │ is_top         │ bit         │ 是否置顶     │
  │ unread_num     │ int         │ 未读消息数   │
  │ last_msg_content │ text        │ 最后消息内容 │
  └────────────────┴─────────────┴──────────────┘

  6. 说说表 (talk)

  ┌─────────────┬─────────────┬────────────────┐
  │ 字段        │ 类型        │ 说明           │
  ├─────────────┼─────────────┼────────────────┤
  │ id          │ varchar(64) │ 主键           │
  │ user_id     │ varchar(64) │ 用户ID         │
  │ content     │ text        │ 说说内容(JSON) │
  │ like_num    │ int         │ 点赞数         │
  │ comment_num │ int         │ 评论数         │
  └─────────────┴─────────────┴────────────────┘

  7. 通知表 (notify)

  ┌─────────┬─────────────┬──────────┐
  │ 字段    │ 类型        │ 说明     │
  ├─────────┼─────────────┼──────────┤
  │ id      │ varchar(64) │ 主键     │
  │ from_id │ varchar(64) │ 发送方   │
  │ to_id   │ varchar(64) │ 目标方   │
  │ type    │ varchar(64) │ 类型     │
  │ status  │ varchar(64) │ 状态     │
  │ content │ text        │ 通知内容 │
  └─────────┴─────────────┴──────────┘

  ---

  四、核心功能模块

  1. 认证流程
   客户端请求公钥 → 获取RSA公钥 → 客户端加密密码 →
   发送登录请求 → 服务端解密 → 验证账号密码 → 生成JWT Token

  关键文件: LoginController.java:26, AuthenticationTokenFilter.java:30

  2. 消息发送流程
   客户端发送消息 → 保存到MySQL → 发送到RocketMQ →
   Consumer消费消息 → 通过WebSocket推送 → 客户端接收

  关键文件: MQProducerService.java:33, UserMessageConsumer.java:14,
  WebSocketService.java:40

  3. WebSocket实时通信
   - 使用Netty实现WebSocket服务器（端口9100）
   - 支持心跳检测（30秒）
   - 维护在线用户映射关系

  关键文件: NettyWebSocketServer.java:25

  4. 视频通话（WebRTC）
   用户A邀请 → WebSocket推送 → 用户B接受 →
   交换Offer/Answer → 交换ICE Candidate → 建立P2P连接

  ---

  五、项目结构

   linyu-server-main/
   ├── admin/              # 管理端相关
   ├── annotation/         # 自定义注解
   ├── config/            # 配置类
   ├── constant/          # 常量定义
   ├── consumer/          # RocketMQ消费者
   ├── controller/        # 18个控制器
   ├── dto/               # 17个数据传输对象
   ├── entity/            # 19个实体类
   ├── exception/         # 全局异常处理
   ├── filter/            # JWT认证过滤器
   ├── interceptor/       # 签名拦截器
   ├── mapper/            # 19个MyBatis Mapper
   ├── runner/            # 启动时运行的任务
   ├── scheduling/        # 定时任务
   ├── service/           # 23个业务服务
   ├── utils/             # 工具类
   ├── vo/                # 视图对象
   └── websocket/         # Netty WebSocket服务

  ---

  六、关键文件位置


  ┌────────────────────────────────┬─────────────────┐
  │ 文件                           │ 说明            │
  ├────────────────────────────────┼─────────────────┤
  │ LinyuServerApplication.java    │ 应用启动类      │
  │ LoginController.java           │ 登录控制器      │
  │ MessageController.java         │ 消息控制器      │
  │ UserController.java            │ 用户控制器      │
  │ FriendController.java          │ 好友控制器      │
  │ NettyWebSocketServer.java      │ WebSocket服务器 │
  │ WebSocketService.java          │ WebSocket服务   │
  │ MQProducerService.java         │ MQ生产者        │
  │ UserMessageConsumer.java       │ 用户消息消费者  │
  │ AuthenticationTokenFilter.java │ 认证过滤器      │
  └────────────────────────────────┴─────────────────┘

  ---

✦ 项目分析已完成！这是一个功能完整的即时通讯系统，支持用户管理、好友关系、群组聊天     
  、实时消息、说说分享、通知推送和视频通话等功能。