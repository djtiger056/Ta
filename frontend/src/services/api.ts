import axios from 'axios'
import {
  ASRConfig,
  SystemConfig,
  TTSConfig,
  VoiceCharacter,
  PromptEnhancerConfig,
  PromptEnhancePreview,
  DailyHabitsConfig,
  DailyHabitsStatus,
  EmoteConfig,
  EmoteConfigResponse,
  EmoteCategoryInfo,
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export const configApi = {
  // 获取系统配置
  getConfig: async (): Promise<SystemConfig> => {
    try {
      console.log('请求配置API: /api/config')
      const response = await api.get('/config')
      console.log('API响应:', response.data)
      return response.data
    } catch (error: any) {
      console.error('配置API错误:', error)
      if (error.response) {
        console.error('响应状态:', error.response.status)
        console.error('响应数据:', error.response.data)
      }
      throw error
    }
  },

  // 更新系统配置
  updateConfig: async (config: SystemConfig): Promise<void> => {
    try {
      console.log('更新配置:', config)
      const response = await api.post('/config', config)
      console.log('更新响应:', response.data)
    } catch (error: any) {
      console.error('更新配置错误:', error)
      if (error.response) {
        console.error('响应状态:', error.response.status)
        console.error('响应数据:', error.response.data)
      }
      throw error
    }
  },

  // 测试LLM连接
  testLLMConnection: async (): Promise<boolean> => {
    try {
      console.log('测试LLM连接...')
      const response = await api.post('/test-llm')
      console.log('测试结果:', response.data)
      return response.data.success
    } catch (error: any) {
      console.error('LLM测试错误:', error)
      return false
    }
  },
}

export const chatApi = {
  // 发送聊天消息
  sendMessage: async (message: string, userId?: string): Promise<string> => {
    const response = await api.post('/chat', {
      message,
      user_id: userId || 'web_user'
    })
    return response.data.response
  },

  // 流式聊天
  streamChat: async (message: string, userId?: string) => {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId || 'web_user'
      }),
    })
    
    if (!response.ok) {
      throw new Error('Stream chat failed')
    }
    
    return response
  },
}

export const ttsApi = {
  // 获取TTS配置
  getTTSConfig: async (): Promise<TTSConfig> => {
    try {
      const response = await api.get('/tts/config')
      return response.data.data
    } catch (error: any) {
      console.error('获取TTS配置错误:', error)
      throw error
    }
  },

  // 更新TTS配置
  updateTTSConfig: async (config: Partial<TTSConfig>): Promise<void> => {
    try {
      const response = await api.post('/tts/config', config)
      console.log('TTS配置更新成功:', response.data)
    } catch (error: any) {
      console.error('更新TTS配置错误:', error)
      throw error
    }
  },

  // 获取语音角色列表
  getVoices: async (): Promise<VoiceCharacter[]> => {
    try {
      const response = await api.get('/tts/voices')
      return response.data.data
    } catch (error: any) {
      console.error('获取语音角色列表错误:', error)
      throw error
    }
  },

  // 合成语音
  synthesize: async (text: string, voice?: string): Promise<Blob> => {
    try {
      const response = await api.post('/tts/synthesize', {
        text,
        voice
      }, {
        responseType: 'blob'
      })
      return response.data
    } catch (error: any) {
      console.error('语音合成错误:', error)
      throw error
    }
  },

  // 测试TTS连接
  testTTSConnection: async (): Promise<boolean> => {
    try {
      const response = await api.post('/tts/test')
      return response.data.success
    } catch (error: any) {
      console.error('TTS连接测试错误:', error)
      return false
    }
  },

  // 千问：上传声音复刻样本并创建/更新音色
  qwenVoiceClone: async (params: {
    file: File
    activate?: boolean
    languageHints?: string
    apiKey?: string
    model?: string
    preferredName?: string
    customizationUrl?: string
    realtimeWsUrl?: string
  }): Promise<any> => {
    const formData = new FormData()
    formData.append('file', params.file)
    formData.append('activate', String(params.activate ?? true))
    if (params.languageHints) {
      formData.append('language_hints', params.languageHints)
    }
    if (params.apiKey) formData.append('api_key', params.apiKey)
    if (params.model) formData.append('model', params.model)
    if (params.preferredName) formData.append('preferred_name', params.preferredName)
    if (params.customizationUrl) formData.append('customization_url', params.customizationUrl)
    if (params.realtimeWsUrl) formData.append('realtime_ws_url', params.realtimeWsUrl)
    const response = await api.post('/tts/qwen/voice-clone', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data.data
  },
}

export const asrApi = {
  getASRConfig: async (): Promise<ASRConfig> => {
    try {
      const response = await api.get('/asr/config')
      return response.data.data
    } catch (error: any) {
      console.error('获取ASR配置错误:', error)
      throw error
    }
  },

  updateASRConfig: async (config: Partial<ASRConfig>): Promise<void> => {
    try {
      const response = await api.post('/asr/config', config)
      console.log('ASR配置更新成功:', response.data)
    } catch (error: any) {
      console.error('更新ASR配置错误:', error)
      throw error
    }
  },

  testASRConnection: async (): Promise<boolean> => {
    try {
      const response = await api.post('/asr/test')
      return response.data.success
    } catch (error: any) {
      console.error('ASR连接测试错误:', error)
      return false
    }
  }
}

export const imageGenApi = {
  // 获取图像生成配置
  getImageGenConfig: async (): Promise<any> => {
    try {
      const response = await api.get('/image-gen/config')
      return response.data.data
    } catch (error: any) {
      console.error('获取图像生成配置错误:', error)
      throw error
    }
  },

  // 更新图像生成配置
  updateImageGenConfig: async (config: any): Promise<void> => {
    try {
      const response = await api.post('/image-gen/config', config)
      console.log('图像生成配置更新成功:', response.data)
    } catch (error: any) {
      console.error('更新图像生成配置错误:', error)
      throw error
    }
  },

  // 生成图像
  generateImage: async (prompt: string): Promise<{ success: boolean; message: string; image_data?: string }> => {
    try {
      const response = await api.post('/image-gen/generate', {
        prompt
      })
      return response.data
    } catch (error: any) {
      console.error('图像生成错误:', error)
      throw error
    }
  },

  // 测试图像生成连接
  testImageGenConnection: async (): Promise<boolean> => {
    try {
      const response = await api.post('/image-gen/test-connection')
      return response.data.success
    } catch (error: any) {
      console.error('图像生成连接测试错误:', error)
      return false
    }
  },
}

export const visionApi = {
  // 获取视觉识别配置
  getVisionConfig: async (): Promise<any> => {
    try {
      const response = await api.get('/vision/config')
      return response.data.data
    } catch (error: any) {
      console.error('获取视觉识别配置错误:', error)
      throw error
    }
  },

  // 更新视觉识别配置
  updateVisionConfig: async (config: any): Promise<void> => {
    try {
      const response = await api.post('/vision/config', config)
      console.log('视觉识别配置更新成功:', response.data)
    } catch (error: any) {
      console.error('更新视觉识别配置错误:', error)
      throw error
    }
  },

  // 测试视觉识别连接
  testVisionConnection: async (): Promise<boolean> => {
    try {
      const response = await api.post('/vision/test-connection')
      return response.data.success
    } catch (error: any) {
      console.error('视觉识别连接测试错误:', error)
      return false
    }
  },

  // 识别图片
  recognizeImage: async (imageUrl?: string, imageData?: string, prompt?: string): Promise<{ success: boolean; message: string; recognition_text?: string }> => {
    try {
      const response = await api.post('/vision/recognize', {
        image_url: imageUrl,
        image_data: imageData,
        prompt
      })
      return response.data
    } catch (error: any) {
      console.error('图片识别错误:', error)
      throw error
    }
  },
}

export const memoryApi = {
  // 获取记忆配置
  getMemoryConfig: async (): Promise<any> => {
    try {
      const response = await api.get('/memory/config')
      return response.data.config
    } catch (error: any) {
      console.error('获取记忆配置错误:', error)
      throw error
    }
  },

  // 更新记忆配置
  updateMemoryConfig: async (config: any): Promise<any> => {
    try {
      const response = await api.post('/memory/config', { config })
      console.log('????????:', response.data)
      return response.data
    } catch (error: any) {
      console.error('????????:', error)
      throw error
    }
  },

  // 获取记忆统计信息
  getMemoryStats: async (): Promise<any> => {
    try {
      const response = await api.get('/memory/stats')
      return response.data
    } catch (error: any) {
      console.error('获取记忆统计错误:', error)
      throw error
    }
  },

  // 获取短期记忆
  getShortTermMemories: async (user_id: string, session_id: string, limit: number = 50): Promise<any> => {
    try {
      const response = await api.get('/memory/short-term', {
        params: { user_id, session_id, limit }
      })
      return response.data.memories
    } catch (error: any) {
      console.error('获取短期记忆错误:', error)
      throw error
    }
  },

  // 获取待处理区原文
  getPendingMemories: async (user_id: string, session_id: string, limit: number = 100): Promise<any> => {
    try {
      const response = await api.get('/memory/pending', {
        params: { user_id, session_id, limit }
      })
      return response.data.memories
    } catch (error: any) {
      console.error('获取待处理区错误:', error)
      throw error
    }
  },

  // 手动触发：摘要待处理区
  summarizePendingMemories: async (user_id: string, session_id: string): Promise<any> => {
    try {
      const response = await api.post('/memory/pending/summarize', null, {
        params: { user_id, session_id }
      })
      return response.data
    } catch (error: any) {
      console.error('触发待处理区摘要错误:', error)
      throw error
    }
  },

  // 获取中期记忆（摘要）
  getMidTermMemories: async (user_id: string, session_id?: string, limit: number = 10): Promise<any> => {
    try {
      const params: any = { user_id, limit }
      if (session_id) params.session_id = session_id
      const response = await api.get('/memory/mid-term', { params })
      return response.data.summaries
    } catch (error: any) {
      console.error('获取中期记忆错误:', error)
      throw error
    }
  },

  // 获取长期记忆
  getLongTermMemories: async (user_id: string, limit: number = 100): Promise<any> => {
    try {
      const response = await api.get('/memory/long-term', {
        params: { user_id, limit }
      })
      return response.data.memories
    } catch (error: any) {
      console.error('获取长期记忆错误:', error)
      throw error
    }
  },

  // 搜索长期记忆
  searchLongTermMemories: async (user_id: string, query: string, top_k: number = 3, score_threshold: number = 0.5): Promise<any> => {
    try {
      const response = await api.post('/memory/long-term/search', {
        user_id,
        query,
        top_k,
        score_threshold
      })
      return response.data.memories
    } catch (error: any) {
      console.error('搜索长期记忆错误:', error)
      throw error
    }
  },

  // 添加长期记忆
  addLongTermMemory: async (user_id: string, content: string, importance: number = 0.5, metadata: any = {}): Promise<void> => {
    try {
      const response = await api.post('/memory/long-term', {
        user_id,
        content,
        importance,
        metadata
      })
      console.log('添加长期记忆成功:', response.data)
    } catch (error: any) {
      console.error('添加长期记忆错误:', error)
      throw error
    }
  },

  // 删除长期记忆
  deleteLongTermMemory: async (memory_id: string): Promise<void> => {
    try {
      const response = await api.delete(`/memory/long-term/${memory_id}`)
      console.log('删除记忆成功:', response.data)
    } catch (error: any) {
      console.error('删除长期记忆错误:', error)
      throw error
    }
  },

  // 更新长期记忆
  updateLongTermMemory: async (memory_id: string, content?: string, importance?: number, metadata?: any): Promise<void> => {
    try {
      const response = await api.put(`/memory/long-term/${memory_id}`, {
        content,
        importance,
        metadata
      })
      console.log('更新记忆成功:', response.data)
    } catch (error: any) {
      console.error('更新长期记忆错误:', error)
      throw error
    }
  },

  // 清除记忆
  clearMemories: async (user_id: string, session_id?: string): Promise<void> => {
    try {
      const response = await api.post('/memory/clear', {
        user_id,
        session_id
      })
      console.log('清除记忆成功:', response.data)
    } catch (error: any) {
      console.error('清除记忆错误:', error)
      throw error
    }
  },

  // 获取用户ID列表
  getMemoryUsers: async (): Promise<{ user_ids: string[] }> => {
    try {
      const response = await api.get('/memory/users')
      return response.data
    } catch (error: any) {
      console.error('获取用户ID列表错误:', error)
      throw error
    }
  },

  // 测试记忆系统
  testMemorySystem: async (): Promise<any> => {
    try {
      const response = await api.get('/memory/test')
      return response.data
    } catch (error: any) {
      console.error('测试记忆系统错误:', error)
      throw error
    }
  },

  // 外部记忆状态
  getExternalMemoryStatus: async (): Promise<any> => {
    try {
      const response = await api.get('/memory/external/ping')
      return response.data
    } catch (error: any) {
      console.error('获取外部记忆状态错误:', error)
      throw error
    }
  },

  // 外部记忆画像
  getExternalMemoryProfiles: async (user_id: string): Promise<any> => {
    try {
      const response = await api.get('/memory/external/profiles', { params: { user_id } })
      return response.data.profiles
    } catch (error: any) {
      console.error('获取外部记忆画像错误:', error)
      throw error
    }
  },

  // 外部记忆事件
  getExternalMemoryEvents: async (user_id: string, limit: number = 10, query?: string): Promise<any> => {
    try {
      const response = await api.get('/memory/external/events', {
        params: { user_id, limit, query }
      })
      return response.data.events
    } catch (error: any) {
      console.error('获取外部记忆事件错误:', error)
      throw error
    }
  },

  // 外部记忆上下文
  getExternalMemoryContext: async (
    user_id: string,
    max_token_size: number = 500,
    prefer_topics?: string[]
  ): Promise<any> => {
    try {
      const response = await api.post('/memory/external/context', {
        user_id,
        max_token_size,
        prefer_topics
      })
      return response.data.context
    } catch (error: any) {
      console.error('获取外部记忆上下文错误:', error)
      throw error
    }
  },
}

export const proactiveApi = {
  getConfig: async (): Promise<any> => {
    const response = await api.get('/proactive/config')
    return response.data.config
  },
  updateConfig: async (cfg: any): Promise<void> => {
    await api.post('/proactive/config', cfg)
  },
  getStatus: async (): Promise<any> => {
    const response = await api.get('/proactive/status')
    return response.data
  },
  triggerOnce: async (payload: { channel: string; user_id: string; session_id?: string; display_name?: string; instruction?: string; }): Promise<string> => {
    const response = await api.post('/proactive/trigger', payload)
    return response.data.message
  }
}

export const promptEnhancerApi = {
  getConfig: async (): Promise<PromptEnhancerConfig> => {
    const response = await api.get('/prompt-enhancer/config')
    return response.data
  },
  updateConfig: async (updates: Partial<PromptEnhancerConfig>): Promise<PromptEnhancerConfig> => {
    const response = await api.put('/prompt-enhancer/config', updates)
    return response.data.config
  },
  preview: async (prompt: string, forceCategories?: string[]): Promise<PromptEnhancePreview> => {
    const response = await api.post('/prompt-enhancer/preview', {
      prompt,
      force_categories: forceCategories
    })
    return response.data
  },
  getWordBanks: async (): Promise<any> => {
    const response = await api.get('/prompt-enhancer/word-banks')
    return response.data
  },
  reloadWordBanks: async (): Promise<void> => {
    await api.post('/prompt-enhancer/word-banks/reload')
  },
  addCustomWords: async (category: string, words: string[]): Promise<any> => {
    const response = await api.post('/prompt-enhancer/word-banks/custom', { category, words })
    return response.data
  },
  deleteCustomWords: async (category: string, words?: string[]): Promise<any> => {
    const response = await api.delete('/prompt-enhancer/word-banks/custom', { 
      data: { category, words } 
    })
    return response.data
  }
}

export const emoteApi = {
  getConfig: async (): Promise<EmoteConfigResponse> => {
    const response = await api.get('/emotes/config')
    return response.data
  },
  updateConfig: async (config: EmoteConfig): Promise<EmoteConfigResponse> => {
    const response = await api.post('/emotes/config', config)
    return response.data
  },
  reloadFiles: async (): Promise<{ success: boolean; categories: EmoteCategoryInfo[]; base_path: string }> => {
    const response = await api.post('/emotes/reload')
    return response.data
  }
}

export const dailyHabitsApi = {
  getConfig: async (): Promise<DailyHabitsConfig> => {
    const response = await api.get('/mcp/daily-habits/config')
    return response.data.config
  },
  saveConfig: async (config: DailyHabitsConfig): Promise<void> => {
    await api.post('/mcp/daily-habits/config', config)
  },
  getStatus: async (): Promise<DailyHabitsStatus> => {
    const response = await api.get('/mcp/daily-habits/status')
    return response.data
  },
}

export const reminderApi = {
  getConfig: async (): Promise<any> => {
    const response = await api.get('/reminder/config')
    return response.data
  },
  updateConfig: async (config: any): Promise<any> => {
    const response = await api.post('/reminder/config', config)
    return response.data
  },
  getReminderList: async (params?: { user_id?: string; session_id?: string; status?: string; limit?: number }): Promise<any> => {
    const response = await api.get('/reminder/list', { params })
    return response.data
  },
  createReminder: async (data: {
    user_id: string
    session_id: string
    content: string
    trigger_time: string
    original_message?: string
    time_expression?: string
    reminder_message?: string
    metadata?: any
  }): Promise<any> => {
    const response = await api.post('/reminder/create', data)
    return response.data
  },
  reminderAction: async (reminderId: number, action: 'complete' | 'cancel'): Promise<any> => {
    const response = await api.post(`/reminder/${reminderId}/action`, { action })
    return response.data
  },
  getPendingReminders: async (): Promise<any> => {
    const response = await api.get('/reminder/pending')
    return response.data
  },
}

export default api
