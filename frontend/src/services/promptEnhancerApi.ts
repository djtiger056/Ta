import axios from 'axios'
import { WordBankCategory, WordBankItem, PresetConfig, PromptEnhancerConfig, PromptEnhancePreview } from '@/types'

const API_BASE = '/api/prompt-enhancer'

export const promptEnhancerApi = {
  // 基础功能
  async getConfig(): Promise<PromptEnhancerConfig> {
    const response = await axios.get(`${API_BASE}/config`)
    return response.data
  },

  async updateConfig(updates: Partial<PromptEnhancerConfig>): Promise<PromptEnhancerConfig> {
    const response = await axios.put(`${API_BASE}/config`, updates)
    return response.data.config
  },

  async preview(prompt: string): Promise<PromptEnhancePreview> {
    const response = await axios.post(`${API_BASE}/preview`, { prompt })
    return response.data
  },

  async enhance(prompt: string): Promise<PromptEnhancePreview> {
    const response = await axios.post(`${API_BASE}/enhance`, { prompt })
    return response.data
  },

  async sampleWords(categories: string[], pickCount?: Record<string, number>): Promise<{ words: Record<string, string[]>; merged: string }> {
    const response = await axios.post(`${API_BASE}/sample`, {
      categories,
      pick_count: pickCount
    })
    return response.data
  },

  async reload(): Promise<{ message: string }> {
    const response = await axios.post(`${API_BASE}/reload`)
    return response.data
  },

  // 分类管理
  async getCategories(): Promise<WordBankCategory[]> {
    const response = await axios.get(`${API_BASE}/categories`)
    return response.data.categories
  },

  async getCategory(path: string): Promise<WordBankCategory> {
    const response = await axios.get(`${API_BASE}/categories/${encodeURIComponent(path)}`)
    return response.data
  },

  async createCategory(path: string, name: string, items?: string[], pick_count?: number): Promise<WordBankCategory> {
    const response = await axios.post(`${API_BASE}/categories`, { path, name, items, pick_count })
    return response.data.category
  },

  async updateCategory(path: string, updates: Partial<WordBankCategory>): Promise<WordBankCategory> {
    const response = await axios.put(`${API_BASE}/categories/${encodeURIComponent(path)}`, updates)
    return response.data.category
  },

  async deleteCategory(path: string): Promise<void> {
    await axios.delete(`${API_BASE}/categories/${encodeURIComponent(path)}`)
  },

  // 词条管理
  async addWords(categoryPath: string, words: string[]): Promise<WordBankItem[]> {
    const response = await axios.post(`${API_BASE}/words`, { category_path: categoryPath, words })
    return response.data.items
  },

  async updateWord(categoryPath: string, wordIndex: number, updates: Partial<WordBankItem>): Promise<WordBankItem> {
    const response = await axios.put(`${API_BASE}/words`, { 
      category_path: categoryPath, 
      word_index: wordIndex, 
      ...updates 
    })
    return response.data.item
  },

  async deleteWords(categoryPath: string, wordIndices: number[]): Promise<WordBankItem[]> {
    const response = await axios.post(`${API_BASE}/words/delete`, { 
      category_path: categoryPath, 
      word_indices: wordIndices 
    })
    return response.data.items
  },

  // 预设管理
  async getPresets(): Promise<PresetConfig[]> {
    const response = await axios.get(`${API_BASE}/presets`)
    return response.data.presets
  },

  async createPreset(
    name: string,
    description: string,
    outfitStyle?: string,
    sceneType?: string,
    categories?: string[],
    pickCountOverrides?: Record<string, number>
  ): Promise<PresetConfig> {
    const response = await axios.post(`${API_BASE}/presets`, {
      name,
      description,
      outfit_style: outfitStyle,
      scene_type: sceneType,
      categories,
      pick_count_overrides: pickCountOverrides
    })
    return response.data.preset
  },

  async updatePreset(
    name: string,
    updates: Partial<PresetConfig> & { pick_count_overrides?: Record<string, number> }
  ): Promise<PresetConfig> {
    const response = await axios.put(`${API_BASE}/presets/${encodeURIComponent(name)}`, updates)
    return response.data.preset
  },

  async deletePreset(name: string): Promise<void> {
    await axios.delete(`${API_BASE}/presets/${encodeURIComponent(name)}`)
  },

  async setCurrentPreset(name: string): Promise<PresetConfig> {
    const response = await axios.put(`${API_BASE}/presets/${encodeURIComponent(name)}/set-current`)
    return response.data.preset
  },

  // 兼容旧接口
  async getWordBanks(): Promise<{ raw: any, tree: any[] }> {
    const response = await axios.get(`${API_BASE}/word-banks`)
    return response.data
  },

  async addCustomWords(category: string, words: string[]): Promise<any> {
    const response = await axios.post(`${API_BASE}/word-banks/custom`, { category_path: category, words })
    return response.data
  },

  async deleteCustomWords(category: string, words?: string[]): Promise<any> {
    const response = await axios.delete(`${API_BASE}/word-banks/custom`, { 
      data: { category_path: category, words } 
    })
    return response.data
  },

  async reloadWordBanks(): Promise<{ message: string }> {
    const response = await axios.post(`${API_BASE}/word-banks/reload`)
    return response.data
  }
}
