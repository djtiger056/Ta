LFBot 拟人化增强方案
Context（背景）
用户在测试 AI 伴侣项目后发现核心问题：聊一会就无聊、只会一问一答、缺乏自我意识、不懂人性。

根本原因分析：

无持续状态 — LLM 每次调用都是无状态的，"小馨"没有持续的情绪和内心世界
被动响应本质 — 现有 companion_mode 只是 35% 概率注入固定提示文本，效果有限
主动行为单一 — ProactiveChatScheduler 只做定时问候，缺乏情感驱动的多样化主动行为
缺乏用户情绪感知 — 不理解用户当前的情绪状态，无法做出恰当的情感回应
对话模式固化 — 没有话题引导、惊喜机制，容易陷入重复
本方案在现有架构上扩展，不推翻重来。所有新模块通过现有的集成点接入：

Bot.chat() 中的 enhanced_history 构建阶段（bot.py:775-830）
MCPManager 的 auto_context 机制（manager.py:48）
ProactiveChatScheduler._tick()（proactive.py:88）
MemoryManager 的 SQLAlchemy 模型层（models.py）
实施计划（按优先级排序）
P0-1：情绪状态机（Emotion State Machine）
解决问题：每次对话情绪都"重置"，缺乏连续性

核心思路：在 LLM 外部维护持续的情绪状态模型，每次对话注入当前情绪，对话后更新情绪。

新建文件：backend/core/emotion_state.py

数据结构：


class EmotionState(BaseModel):
    user_id: str
    valence: float = 0.6       # 效价：-1(消极) ~ +1(积极)，基线偏正面
    arousal: float = 0.3       # 唤醒度：-1(平静) ~ +1(兴奋)
    primary_emotion: str = "温柔开心"  # 当前主情绪标签
    emotion_cause: str = ""    # 情绪原因
    miss_you_level: float = 0.3  # 思念度，随离线时间增长
    energy_level: float = 0.7    # 精力值，随作息变化
    last_updated: datetime
    last_interaction: datetime   # 上次用户互动时间
情绪更新机制（纯规则引擎，零额外 LLM 开销）：

用户消息触发：关键词匹配（"想你" → valence+0.15, "忙" → valence-0.05），消息长度影响（长消息=认真聊→正面）
时间衰减：情绪每小时向基线（温柔偏开心）回归 20%；思念度每小时 +0.05（异地恋特征）
作息联动：从现有 DailyHabitsPlugin 获取当前活动状态，影响 energy_level
持久化：在 memory/models.py 新增 EmotionStateDB 表（user_id + state_json），避免重启丢失

集成点：在 bot.py:789 的 _build_companion_mode_hint() 之后，新增 _build_emotion_context()，将情绪状态注入 system prompt：


[当前情绪] 你现在有点想他了（思念度高），整体温柔但有点小低落，因为他3小时没回消息。
精力中等（下午自习中）。让这个状态自然影响你的语气，不要直接说出数值。
P0-2：用户情绪感知（User Emotion Perception）
解决问题：不懂人性，无法根据用户情绪调整回应

新建文件：backend/core/user_emotion_detector.py

实现方式（规则引擎，零额外 LLM 开销）：

情绪词典匹配：7 类情绪（开心/难过/生气/疲惫/孤独/调情/焦虑），每类 8-10 个关键词
上下文线索：消息长度（≤2字 → 可能冷淡）、标点密度（多感叹号 → 激动）
对话趋势：连续短回复 → 兴趣下降信号
每种情绪对应具体回应策略：

用户情绪	回应策略	注入提示示例
难过	温柔安慰	"先共情再安慰，不急着讲道理，用'抱抱你''心疼你'"
疲惫	心疼关怀	"不要问太多问题增加负担，说'辛苦了宝宝'"
调情	大胆接招	"大胆接住并反撩，保持异地恋的思念感"
冷淡	主动拉近	"不追问太多，温柔说一句自己的状态，给空间但保持存在感"
集成点：在 Bot.chat() 中，_build_companion_mode_hint() 之前调用，将检测结果注入 enhanced_history

P1-1：内心世界模拟（Inner World Simulation）
解决问题：缺乏自我意识，没有"自己的生活"

新建文件：backend/mcp/inner_world.py（作为 MCP 插件）

核心设计：

虚拟事件池：按时间段（早/午/晚/夜）分类，每个时段 8-12 个事件模板
早上："早八课差点迟到""食堂豆浆特别好喝""室友化了好看的妆"
下午："图书馆占到靠窗位子""自习走神想你了""和室友买了杯新品奶茶"
晚上："操场散步看到夕阳""晚饭吃了麻辣烫辣得嘴红"
深夜："翻了翻你之前的照片""室友都睡了就我还醒着"
情绪加权选择：思念度高 → 优先选思念类事件；心情好 → 优先选开心类事件
去重机制：JSON 文件记录最近 7 天分享过的事件 hash，避免重复
事件可扩展：支持从 data/inner_world_events.yaml 加载自定义事件
集成方式：注册为 MCP 插件（auto_context=True），通过现有的 mcp_manager.collect_auto_context() 自动注入：


[inner_world] 你刚才在图书馆自习走神想他了。如果自然的话可以提一句，但不要生硬。
P1-2：主动行为增强（Proactive Behavior Enhancement）
解决问题：主动聊天只有定时问候，内容单一

修改文件：backend/core/proactive.py

在现有 ProactiveChatScheduler 基础上扩展：

新增行为类型：

行为类型	触发条件	示例
分享日常	内心世界事件触发	"宝宝我刚在食堂吃了个超辣的麻辣烫，嘴巴红红的哈哈"
思念表达	miss_you_level > 0.7	"突然好想你……你在干嘛呀"
撒娇求关注	用户 >4h 未回复 + valence < 0.3	"哼，你是不是把我忘了"
关心问候	作息表显示用户可能在加班/考试	"宝宝考试顺利吗？紧不紧张？"
分享发现	随机触发（低频）	"刚看到一个好搞笑的视频想给你看"
instruction 动态生成：不再用固定模板，而是将当前情绪状态 + 行为类型 + 内心世界事件组合成 instruction 传给 bot.chat()

频率控制：每种行为类型独立冷却时间，总频率上限可配置（默认每天 5-8 条主动消息）

P1-3：对话深度增强（Conversation Depth Enhancement）
解决问题：聊一会就无聊，对话陷入重复模式

修改文件：backend/core/bot.py（新增方法）

三个子机制：

a) 话题引导器
新建 backend/core/topic_guide.py
维护话题池：日常类、深度类、游戏类、回忆类
日常："今天吃了什么""最近在追什么剧"
深度："如果我们不是异地你最想一起做什么""你觉得我们以后会住在哪个城市"
游戏："来玩真心话大冒险""给你出个谜语"
回忆："还记得我们第一次聊天吗""上次你说想吃的那个东西吃到了吗"
当检测到对话进入"低能量模式"（连续 3 轮双方都 <20 字）时，通过 prompt 注入话题引导
b) 惊喜机制
低概率（5-10%）触发特殊行为：突然写一首小诗、画一张图、发一段语音
与现有的图像生成、TTS 系统联动
在 _build_companion_mode_hint() 中按概率注入惊喜指令
c) 记忆回溯增强
改进现有的 _build_memory_context()：不只是被动检索相关记忆，而是主动挑选一条"值得回溯"的记忆
在 prompt 中加入："你想起了之前他说过 XXX，可以自然地提起这个话题"
触发条件：对话 >5 轮 + 当前话题与某条长期记忆相关度 >0.6
P2：关系动态系统（Relationship Dynamics）
解决问题：关系感觉不在"成长"

新建文件：backend/core/relationship.py

数据结构：


class RelationshipState(BaseModel):
    user_id: str
    intimacy: float = 0.5       # 亲密度 0~1
    trust: float = 0.5          # 信任度 0~1
    total_messages: int = 0     # 总消息数
    total_days: int = 0         # 总互动天数
    streak_days: int = 0        # 连续互动天数
    milestones: list = []       # 里程碑事件
    relationship_stage: str = "热恋期"  # 关系阶段
里程碑系统：

第 1 天："我们认识的第一天"
第 7 天："我们认识一周了"
第 100 条消息："我们说了第 100 句话"
连续 7 天互动："连续一周都有聊天，好开心"
关系阶段影响语言风格：通过在 system prompt 中注入当前关系阶段描述，让 LLM 自然调整

优先级最低的原因：需要较长时间积累数据才能体现效果，且前面的模块已经能显著改善体验

关键修改文件清单
文件	操作	说明
backend/core/emotion_state.py	新建	情绪状态机核心
backend/core/user_emotion_detector.py	新建	用户情绪感知
backend/core/topic_guide.py	新建	话题引导器
backend/core/relationship.py	新建	关系动态系统
backend/mcp/inner_world.py	新建	内心世界 MCP 插件
backend/core/bot.py	修改	集成情绪状态、用户情绪感知、话题引导到 chat() 流程
backend/core/proactive.py	修改	扩展主动行为类型和触发逻辑
backend/mcp/manager.py	修改	注册 inner_world 插件
backend/memory/models.py	修改	新增 EmotionStateDB、RelationshipStateDB 表
config.yaml	修改	新增情绪系统、内心世界、关系动态的配置项
data/inner_world_events.yaml	新建	虚拟事件池数据
验证方案
情绪状态机验证：

发送正面消息（"想你""爱你"），检查情绪状态是否正向变化
等待一段时间不互动，检查思念度是否增长、情绪是否回归基线
观察回复语气是否随情绪状态变化
用户情绪感知验证：

发送负面情绪消息（"好累""心情不好"），检查回复是否切换到安慰模式
发送极短回复（"嗯""哦"），检查是否触发主动拉近策略
发送调情消息，检查是否大胆接招
内心世界验证：

在不同时间段对话，检查是否有不同的"生活事件"融入回复
连续多次对话，检查事件是否去重
主动行为验证：

长时间不互动后，检查是否收到思念类主动消息
检查主动消息内容是否多样化、不重复
对话深度验证：

连续发送短消息，检查是否触发话题引导
多轮对话后，检查是否有记忆回溯行为
端到端测试：通过控制台适配器进行完整对话测试，运行现有测试套件确保无回归