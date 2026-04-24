import React, { useEffect, useMemo, useState } from 'react'
import {
  Card,
  Switch,
  Button,
  Input,
  Space,
  Tag,
  message,
  Divider,
  Typography,
  Row,
  Col,
  Modal,
  List,
  Select,
  Tooltip,
  Table,
  Popconfirm,
  Form,
  InputNumber,
  Tabs,
  Badge
} from 'antd'
import {
  HighlightOutlined,
  ReloadOutlined,
  EyeOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  FolderOutlined,
  TagsOutlined,
  StarOutlined
} from '@ant-design/icons'
import { promptEnhancerApi } from '@/services/promptEnhancerApi'
import { WordBankCategory, WordBankItem, PresetConfig, PromptEnhancerConfig, PromptEnhancePreview, IntentRule } from '@/types'

const { TextArea } = Input
const { Title, Paragraph, Text } = Typography
const { TabPane } = Tabs

const PromptEnhancerPage: React.FC = () => {
  const [config, setConfig] = useState<PromptEnhancerConfig | null>(null)
  const [categories, setCategories] = useState<WordBankCategory[]>([])
  const [intents, setIntents] = useState<IntentRule[]>([])
  const [presets, setPresets] = useState<PresetConfig[]>([])
  const [testPrompt, setTestPrompt] = useState('一张女生自拍照，微笑看向镜头')
  const [preview, setPreview] = useState<PromptEnhancePreview | null>(null)
  const [loading, setLoading] = useState({
    config: false,
    preview: false,
    categories: false,
    presets: false,
    saving: false,
    sampling: false
  })
  
  // 编辑状态
  const [editingCategory, setEditingCategory] = useState<string | null>(null)
  const [editingWordItem, setEditingWordItem] = useState<{ category: string, index: number, item: WordBankItem } | null>(null)
  const [editingPreset, setEditingPreset] = useState<PresetConfig | null>(null)
  const [editingIntent, setEditingIntent] = useState<IntentRule | null>(null)
  
  // 模态框状态
  const [categoryModalVisible, setCategoryModalVisible] = useState(false)
  const [presetModalVisible, setPresetModalVisible] = useState(false)
  const [intentModalVisible, setIntentModalVisible] = useState(false)
  const [wordModalVisible, setWordModalVisible] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [pickOverrides, setPickOverrides] = useState<Record<string, number>>({})
  const [sampleResult, setSampleResult] = useState<Record<string, string[]>>({})
  const [presetCategorySelection, setPresetCategorySelection] = useState<string[]>([])
  const [presetPickOverrides, setPresetPickOverrides] = useState<Record<string, number>>({})
  const [intentCategorySelection, setIntentCategorySelection] = useState<string[]>([])
  const [intentPickOverrides, setIntentPickOverrides] = useState<Record<string, number>>({})
  
  // 表单实例
  const [categoryForm] = Form.useForm()
  const [presetForm] = Form.useForm()
  const [intentForm] = Form.useForm()
  const [wordForm] = Form.useForm()

  const categoryOptions = useMemo(() => {
    const groups: Record<string, { label: string; options: { label: string; value: string }[] }> = {}
    categories.forEach((cat) => {
      const parts = cat.path.split('.')
      const groupKey = parts.length > 1 ? parts[1] : parts[0]
      if (!groups[groupKey]) {
        groups[groupKey] = { label: groupKey, options: [] }
      }
      groups[groupKey].options.push({
        label: `${cat.name}（${cat.path}${cat.is_builtin ? ' · 内置' : ''}）`,
        value: cat.path
      })
    })

    return Object.keys(groups)
      .sort()
      .map((key) => ({
        label: `${groups[key].label}（${groups[key].options.length}）`,
        options: groups[key].options.sort((a, b) => a.value.localeCompare(b.value))
      }))
  }, [categories])

  useEffect(() => {
    loadConfig()
    loadCategories()
    loadPresets()
  }, [])

  useEffect(() => {
    setPickOverrides((prev) => {
      const next: Record<string, number> = {}
      selectedCategories.forEach((path) => {
        next[path] = prev[path] ?? categories.find((c) => c.path === path)?.pick_count ?? 1
      })
      return next
    })
  }, [selectedCategories, categories])

  useEffect(() => {
    setPresetPickOverrides((prev) => {
      const next: Record<string, number> = {}
      presetCategorySelection.forEach((path) => {
        next[path] = prev[path] ?? categories.find((c) => c.path === path)?.pick_count ?? 1
      })
      return next
    })
  }, [presetCategorySelection, categories])

  useEffect(() => {
    setIntentPickOverrides((prev) => {
      const next: Record<string, number> = {}
      intentCategorySelection.forEach((path) => {
        next[path] = prev[path] ?? categories.find((c) => c.path === path)?.pick_count ?? 1
      })
      return next
    })
  }, [intentCategorySelection, categories])

  const loadConfig = async () => {
    try {
      setLoading(prev => ({ ...prev, config: true }))
      const data = await promptEnhancerApi.getConfig()
      setConfig(data)
      setIntents(data.intents || [])
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(prev => ({ ...prev, config: false }))
    }
  }

  const loadCategories = async () => {
    try {
      setLoading(prev => ({ ...prev, categories: true }))
      const data = await promptEnhancerApi.getCategories()
      setCategories(data)
    } catch (error) {
      message.error('加载分类失败')
    } finally {
      setLoading(prev => ({ ...prev, categories: false }))
    }
  }

  const loadPresets = async () => {
    try {
      setLoading(prev => ({ ...prev, presets: true }))
      const data = await promptEnhancerApi.getPresets()
      setPresets(data)
    } catch (error) {
      message.error('加载预设失败')
    } finally {
      setLoading(prev => ({ ...prev, presets: false }))
    }
  }

  const updateConfig = async (updates: Partial<PromptEnhancerConfig>): Promise<PromptEnhancerConfig | null> => {
    if (!config) return null
    try {
      setLoading(prev => ({ ...prev, saving: true }))
      const updated = await promptEnhancerApi.updateConfig(updates)
      setConfig(updated)
      setIntents(updated.intents || [])
      message.success('配置已更新')
      return updated
    } catch (error) {
      message.error('更新配置失败')
      return null
    } finally {
      setLoading(prev => ({ ...prev, saving: false }))
    }
  }

  // 意图管理
  const handleToggleIntent = async (name: string, enabled: boolean) => {
    const next = intents.map((intent) =>
      intent.name === name ? { ...intent, enabled } : intent
    )
    await updateConfig({ intents: next })
  }

  const openIntentModal = (intent?: IntentRule) => {
    const target = intent || null
    setEditingIntent(target)
    setIntentCategorySelection(target?.categories || [])
    setIntentPickOverrides(target?.pick_count_overrides || {})
    intentForm.setFieldsValue({
      name: target?.name,
      description: target?.description,
      keywords: target?.keywords?.join('\n') || '',
      enabled: target?.enabled ?? true
    })
    setIntentModalVisible(true)
  }

  const handleSaveIntent = async (values: any) => {
    const keywords = (values.keywords || '')
      .split(/[\n,]/)
      .map((kw: string) => kw.trim())
      .filter(Boolean)

    if (!editingIntent && intents.find((i) => i.name === values.name)) {
      message.error('已存在同名意图')
      return
    }

    const next: IntentRule[] = [...intents]
    if (editingIntent) {
      const idx = next.findIndex((i) => i.name === editingIntent.name)
      if (idx >= 0) {
        next[idx] = {
          ...next[idx],
          name: editingIntent.name,
          description: values.description || '',
          keywords,
          categories: intentCategorySelection,
          pick_count_overrides: intentPickOverrides,
          enabled: values.enabled ?? true
        }
      }
    } else {
      next.push({
        name: values.name,
        description: values.description || '',
        keywords,
        categories: intentCategorySelection,
        pick_count_overrides: intentPickOverrides,
        enabled: values.enabled ?? true
      })
    }

    const updated = await updateConfig({ intents: next })
    if (updated) {
      setIntentModalVisible(false)
      setEditingIntent(null)
      setIntentCategorySelection([])
      setIntentPickOverrides({})
      intentForm.resetFields()
    }
  }

  const handleDeleteIntent = async (name: string) => {
    const next = intents.filter((i) => i.name !== name)
    await updateConfig({ intents: next })
  }

  const handleCategoryToggle = (path: string, enabled: boolean) => {
    updateConfig({
      categories: {
        ...config?.categories,
        [path]: enabled
      }
    })
  }

  const handlePickCountChange = (path: string, count: number) => {
    updateConfig({
      pick_count: {
        ...config?.pick_count,
        [path]: count
      }
    })
  }

  const handlePresetChange = async (presetName: string) => {
    try {
      await promptEnhancerApi.setCurrentPreset(presetName)
      await loadConfig()
      message.success('预设已切换')
    } catch (error) {
      message.error('切换预设失败')
    }
  }

  const previewEnhancement = async () => {
    try {
      setLoading(prev => ({ ...prev, preview: true }))
      const result = await promptEnhancerApi.preview(testPrompt)
      setPreview(result)
    } catch (error) {
      message.error('预览失败')
    } finally {
      setLoading(prev => ({ ...prev, preview: false }))
    }
  }

  const reloadAll = async () => {
    try {
      await promptEnhancerApi.reload()
      await loadConfig()
      await loadCategories()
      await loadPresets()
      message.success('已重新加载')
    } catch (error) {
      message.error('重载失败')
    }
  }

  const handleSampleWords = async () => {
    if (!selectedCategories.length) {
      message.warning('请先选择要抽取的分类')
      return
    }

    try {
      setLoading((prev) => ({ ...prev, sampling: true }))
      const result = await promptEnhancerApi.sampleWords(selectedCategories, pickOverrides)
      setSampleResult(result.words || {})
      message.success('已完成抽取')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '抽取失败')
    } finally {
      setLoading((prev) => ({ ...prev, sampling: false }))
    }
  }

  const handleAppendSampleToPrompt = () => {
    const merged = Object.values(sampleResult).flat().join('，')
    if (!merged) {
      message.info('暂未有抽取结果可填充')
      return
    }
    setTestPrompt((prev) => (prev ? `${prev}，${merged}` : merged))
    message.success('已将抽取结果填入测试区')
  }

  // 分类管理
  const handleCreateCategory = async (values: any) => {
    try {
      if (editingCategory) {
        await promptEnhancerApi.updateCategory(editingCategory, {
          name: values.name,
          pick_count: values.pick_count
        })
        message.success('分类已更新')
      } else {
        await promptEnhancerApi.createCategory(
          values.path,
          values.name,
          values.items?.split('\n').filter(Boolean),
          values.pick_count
        )
        message.success('分类已创建')
      }
      setCategoryModalVisible(false)
      setEditingCategory(null)
      categoryForm.resetFields()
      await loadCategories()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    }
  }

  const handleUpdateCategory = async (path: string, updates: any) => {
    try {
      await promptEnhancerApi.updateCategory(path, updates)
      await loadCategories()
      setEditingCategory(null)
      message.success('分类已更新')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新失败')
    }
  }

  const handleDeleteCategory = async (path: string) => {
    try {
      await promptEnhancerApi.deleteCategory(path)
      await loadCategories()
      message.success('分类已删除')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  // 词条管理
  const handleAddWords = async (values: any) => {
    try {
      const words = values.words.split('\n').filter(Boolean)
      await promptEnhancerApi.addWords(selectedCategory, words)
      setWordModalVisible(false)
      wordForm.resetFields()
      await loadCategories()
      message.success('词条已添加')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '添加失败')
    }
  }

  const handleUpdateWord = async (category: string, index: number, updates: any) => {
    try {
      await promptEnhancerApi.updateWord(category, index, updates)
      await loadCategories()
      setEditingWordItem(null)
      message.success('词条已更新')
    } catch (error: any) {
      const detail = error.response?.data?.detail
      if (detail && detail.includes('不允许编辑内置分类')) {
        message.error('无法编辑内置词条，请在左侧开启"允许编辑内置词库"选项')
      } else {
        message.error(detail || '更新失败')
      }
    }
  }

  const handleDeleteWords = async (category: string, indices: number[]) => {
    try {
      await promptEnhancerApi.deleteWords(category, indices)
      await loadCategories()
      message.success('词条已删除')
    } catch (error: any) {
      const detail = error.response?.data?.detail
      if (detail && detail.includes('不允许编辑内置分类')) {
        message.error('无法删除内置词条，请在左侧开启"允许编辑内置词库"选项')
      } else {
        message.error(detail || '删除失败')
      }
    }
  }

  // 预设管理
  const handleSavePreset = async (values: any) => {
    try {
      setLoading((prev) => ({ ...prev, saving: true }))
      if (editingPreset) {
        const updates: any = {
          description: values.description,
          outfit_style: values.outfit_style,
          scene_type: values.scene_type,
          categories: presetCategorySelection,
          pick_count_overrides: presetPickOverrides
        }
        if (values.enabled !== undefined) {
          updates.enabled = values.enabled
        }
        await promptEnhancerApi.updatePreset(editingPreset.name, updates)
        message.success('预设已更新')
      } else {
        await promptEnhancerApi.createPreset(
          values.name,
          values.description,
          values.outfit_style,
          values.scene_type,
          presetCategorySelection,
          presetPickOverrides
        )
        message.success('预设已创建')
      }
      setPresetModalVisible(false)
      setEditingPreset(null)
      presetForm.resetFields()
      setPresetCategorySelection([])
      setPresetPickOverrides({})
      await loadPresets()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存预设失败')
    } finally {
      setLoading((prev) => ({ ...prev, saving: false }))
    }
  }

  const handleDeletePreset = async (name: string) => {
    try {
      await promptEnhancerApi.deletePreset(name)
      await loadPresets()
      message.success('预设已删除')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  // 词条表格列定义 - 接收category参数
  const getWordColumns = (category: WordBankCategory) => [
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 60,
      render: (enabled: boolean, record: WordBankItem, index: number) => {
        const canEdit = !category.is_builtin || config?.allow_edit_builtin
        return canEdit ? (
          <Switch
            size="small"
            checked={enabled}
            onChange={(checked) => handleUpdateWord(category.path, index, { enabled: checked })}
          />
        ) : (
          <Tag color={enabled ? 'green' : 'default'}>
            {enabled ? '启用' : '禁用'}
          </Tag>
        )
      }
    },
    {
      title: '词条',
      dataIndex: 'text',
      render: (text: string, record: WordBankItem, index: number) => {
        const isEditing = editingWordItem?.category === category.path && editingWordItem?.index === index
        const canEdit = !category.is_builtin || config?.allow_edit_builtin
        
        if (isEditing && canEdit) {
          return (
            <Input
              size="small"
              defaultValue={text}
              onPressEnter={(e) => {
                const newText = (e.target as HTMLInputElement).value
                handleUpdateWord(category.path, index, { text: newText })
              }}
              onBlur={(e) => {
                const newText = (e.target as HTMLInputElement).value
                handleUpdateWord(category.path, index, { text: newText })
              }}
            />
          )
        }
        
        return (
          <span
            style={{ 
              cursor: canEdit ? 'pointer' : 'default',
              color: canEdit ? 'inherit' : '#666'
            }}
            onClick={() => canEdit && setEditingWordItem({ category: category.path, index, item: record })}
          >
            {text}
            {category.is_builtin && !config?.allow_edit_builtin && (
              <Tag color="blue" style={{ marginLeft: 8 }}>内置</Tag>
            )}
          </span>
        )
      }
    },
    {
      title: '权重',
      dataIndex: 'weight',
      width: 80,
      render: (weight: number, record: WordBankItem, index: number) => {
        const canEdit = !category.is_builtin || config?.allow_edit_builtin
        return canEdit ? (
          <InputNumber
            size="small"
            min={1}
            max={10}
            value={weight}
            onChange={(value) => handleUpdateWord(category.path, index, { weight: value || 1 })}
          />
        ) : (
          <span style={{ color: '#666' }}>{weight}</span>
        )
      }
    },
    {
      title: '操作',
      width: 80,
      render: (_: any, record: WordBankItem, index: number) => {
        const canEdit = !category.is_builtin || config?.allow_edit_builtin
        return canEdit ? (
          <Popconfirm
            title="确定删除这个词条吗？"
            onConfirm={() => handleDeleteWords(category.path, [index])}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        ) : (
          <Tooltip title="内置词条，需要开启编辑权限">
            <Button size="small" icon={<DeleteOutlined />} disabled />
          </Tooltip>
        )
      }
    }
  ]

  if (!config) return <div style={{ padding: 24 }}>加载中...</div>

  return (
    <div style={{ padding: 24 }}>
      <Title level={2} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <HighlightOutlined /> 提示词增强
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 960 }}>
        完整的词库管理系统，支持分类管理、词条编辑和自定义预设配置。
      </Paragraph>

      <Row gutter={[16, 16]}>
        {/* 左侧配置面板 */}
        <Col span={8}>
          {/* 基础设置 */}
          <Card loading={loading.config}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong style={{ fontSize: 16 }}>启用增强</Text>
                <Switch checked={config.enabled} onChange={(v) => updateConfig({ enabled: v })} />
              </div>

              <div>
                <Text strong>当前预设</Text>
                <Select
                  value={config.current_preset}
                  style={{ width: '100%', marginTop: 8 }}
                  onChange={handlePresetChange}
                  options={presets.map(p => ({
                    value: p.name,
                    label: (
                      <div>
                        <span>{p.description}</span>
                        {p.name === config.current_preset && <Tag color="blue" style={{ marginLeft: 8 }}>当前</Tag>}
                      </div>
                    )
                  }))}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>允许编辑内置词库</Text>
                  <Paragraph style={{ margin: '4px 0 0', fontSize: 12 }} type="secondary">
                    开启后可修改系统内置的词条
                  </Paragraph>
                </div>
                <Switch 
                  checked={config.allow_edit_builtin || false} 
                  onChange={(v) => updateConfig({ allow_edit_builtin: v })} 
                />
              </div>

              <Button icon={<ReloadOutlined />} onClick={reloadAll} loading={loading.config} block>
                重载所有数据
              </Button>
            </Space>
          </Card>

          {/* 预设管理 */}
          <Card 
            title={
              <Space>
                <StarOutlined />
                预设管理
              </Space>
            }
            extra={
              <Button
                size="small"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingPreset(null)
                  presetForm.resetFields()
                  setPresetCategorySelection([])
                  setPresetPickOverrides({})
                  presetForm.setFieldsValue({ enabled: true, outfit_style: 'random', scene_type: 'random' })
                  setPresetModalVisible(true)
                }}
              >
                新建
              </Button>
            }
            style={{ marginTop: 16 }}
          >
            <List
              size="small"
              dataSource={presets}
              renderItem={(preset) => (
                <List.Item
                  actions={[
                    <Button size="small" icon={<EditOutlined />} onClick={() => {
                      setEditingPreset(preset)
                      setPresetCategorySelection(preset.categories || [])
                      setPresetPickOverrides(preset.pick_count_overrides || {})
                      presetForm.setFieldsValue({
                        ...preset,
                        enabled: preset.enabled ?? true
                      })
                      setPresetModalVisible(true)
                    }} />,
                    preset.name !== config.current_preset && (
                      <Popconfirm
                        title="确定删除这个预设吗？"
                        onConfirm={() => handleDeletePreset(preset.name)}
                      >
                        <Button size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    )
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        {preset.description}
                        {preset.name === config.current_preset && <Badge status="processing" text="当前" />}
                      </Space>
                    }
                    description={`穿搭: ${preset.outfit_style} | 场景: ${preset.scene_type}${
                      preset.categories?.length ? ` | 抽取分类: ${preset.categories.length}` : ''
                    }`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 右侧主要内容 */}
        <Col span={16}>
          <Tabs defaultActiveKey="categories">
            {/* 分类管理标签页 */}
            <TabPane tab={<><FolderOutlined /> 分类管理</>} key="categories">
              <Card
                title={
                  <Space>
                    <span>词库分类</span>
                    <Tag color="blue">
                      内置 {categories.filter(c => c.is_builtin).length}
                    </Tag>
                    <Tag color="green">
                      自定义 {categories.filter(c => !c.is_builtin).length}
                    </Tag>
                  </Space>
                }
                extra={
                  <Button icon={<PlusOutlined />} onClick={() => setCategoryModalVisible(true)}>
                    新建分类
                  </Button>
                }
              >
                <Table
                  dataSource={categories}
                  rowKey="path"
                  pagination={false}
                  size="small"
                  expandable={{
                    expandedRowRender: (record: WordBankCategory) => (
                      <Table
                        dataSource={record.items}
                        rowKey={(item, index) => `${item.text}-${index ?? 0}`}
                        columns={getWordColumns(record)}
                        pagination={false}
                        size="small"
                        title={() => {
                          const canEdit = !record.is_builtin || config?.allow_edit_builtin
                          return (
                            <Space>
                              <Text>词条列表</Text>
                              <Button 
                                size="small" 
                                icon={<PlusOutlined />}
                                onClick={() => {
                                  setSelectedCategory(record.path)
                                  setWordModalVisible(true)
                                }}
                                disabled={!canEdit}
                              >
                                添加词条
                              </Button>
                              {!canEdit && record.is_builtin && (
                                <Tag color="blue">需要开启编辑权限</Tag>
                              )}
                            </Space>
                          )
                        }}
                      />
                    )
                  }}
                  columns={[
                    {
                      title: '分类',
                      dataIndex: 'name',
                      render: (text: string, record: WordBankCategory) => (
                        <Space>
                          <Text strong>{text}</Text>
                          {record.is_builtin && <Tag color="blue">内置</Tag>}
                          <Text code style={{ fontSize: 12 }}>{record.path}</Text>
                        </Space>
                      )
                    },
                    {
                      title: '状态',
                      dataIndex: 'enabled',
                      width: 80,
                      render: (enabled: boolean, record: WordBankCategory) => {
                        const canEdit = !record.is_builtin || config?.allow_edit_builtin
                        return canEdit ? (
                          <Switch
                            size="small"
                            checked={enabled}
                            onChange={(checked) => handleCategoryToggle(record.path, checked)}
                          />
                        ) : (
                          <Tag color={enabled ? 'green' : 'default'}>
                            {enabled ? '启用' : '禁用'}
                          </Tag>
                        )
                      }
                    },
                    {
                      title: '抽取数',
                      dataIndex: 'pick_count',
                      width: 100,
                      render: (count: number, record: WordBankCategory) => (
                        <InputNumber
                          size="small"
                          min={0}
                          max={5}
                          value={count}
                          onChange={(value) => handlePickCountChange(record.path, value || 1)}
                        />
                      )
                    },
                    {
                      title: '词条数',
                      dataIndex: 'items',
                      width: 80,
                      render: (items: WordBankItem[]) => items.length
                    },
                    {
                      title: '操作',
                      width: 120,
                      render: (_: any, record: WordBankCategory) => {
                        const canEdit = !record.is_builtin || config?.allow_edit_builtin
                        return (
                          <Space>
                            <Button 
                              size="small" 
                              icon={<EditOutlined />}
                              onClick={() => {
                                setEditingCategory(record.path)
                                categoryForm.setFieldsValue({
                                  path: record.path,
                                  name: record.name,
                                  pick_count: record.pick_count
                                })
                                setCategoryModalVisible(true)
                              }}
                              disabled={!canEdit}
                            >
                              编辑
                            </Button>
                            {!record.is_builtin ? (
                              <Popconfirm
                                title="确定删除这个分类吗？"
                                onConfirm={() => handleDeleteCategory(record.path)}
                              >
                                <Button size="small" danger icon={<DeleteOutlined />} />
                              </Popconfirm>
                            ) : canEdit ? (
                              <Popconfirm
                                title="确定删除这个内置分类吗？此操作不可恢复！"
                                onConfirm={() => handleDeleteCategory(record.path)}
                              >
                                <Button size="small" danger icon={<DeleteOutlined />} />
                              </Popconfirm>
                            ) : (
                              <Tooltip title="内置分类，需要开启编辑权限">
                                <Button size="small" icon={<DeleteOutlined />} disabled />
                              </Tooltip>
                            )}
                          </Space>
                        )
                      }
                    }
                  ]}
                />
              </Card>
            </TabPane>

            <TabPane tab={<><SettingOutlined /> 意图管理</>} key="intents">
              <Card
                title="意图/触发配置"
                extra={
                  <Button size="small" icon={<PlusOutlined />} onClick={() => openIntentModal()}>
                    新增意图
                  </Button>
                }
              >
                <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                  通过关键词命中不同意图，自动使用对应的增强分类；支持人像、风景等多目的扩展。
                </Paragraph>
                <Table
                  size="small"
                  rowKey="name"
                  pagination={false}
                  dataSource={intents}
                  columns={[
                    {
                      title: '名称',
                      dataIndex: 'name',
                      render: (text: string, record: IntentRule) => (
                        <Space>
                          <Text strong>{text}</Text>
                          {record.description && <Text type="secondary">{record.description}</Text>}
                        </Space>
                      )
                    },
                    {
                      title: '状态',
                      dataIndex: 'enabled',
                      width: 100,
                      render: (enabled: boolean, record: IntentRule) => (
                        <Switch
                          size="small"
                          checked={enabled !== false}
                          onChange={(v) => handleToggleIntent(record.name, v)}
                        />
                      )
                    },
                    {
                      title: '关键词',
                      dataIndex: 'keywords',
                      render: (keywords: string[] = []) => (
                        <Space wrap>
                          {keywords.length
                            ? keywords.slice(0, 6).map((kw) => (
                                <Tag key={kw} color="geekblue">
                                  {kw}
                                </Tag>
                              ))
                            : <Text type="secondary">未配置</Text>}
                          {keywords.length > 6 && <Tag>+{keywords.length - 6}</Tag>}
                        </Space>
                      )
                    },
                    {
                      title: '增强分类',
                      dataIndex: 'categories',
                      render: (cats: string[] = []) => (
                        <Space wrap>
                          {cats.length
                            ? cats.map((c) => (
                                <Tag key={c} color="green">
                                  {c}
                                </Tag>
                              ))
                            : <Text type="secondary">未设置</Text>}
                        </Space>
                      )
                    },
                    {
                      title: '操作',
                      width: 160,
                      render: (_: any, record: IntentRule) => (
                        <Space>
                          <Button
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => openIntentModal(record)}
                          >
                            编辑
                          </Button>
                          <Popconfirm
                            title="确认删除该意图？"
                            onConfirm={() => handleDeleteIntent(record.name)}
                          >
                            <Button size="small" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </Space>
                      )
                    }
                  ]}
                />
              </Card>
            </TabPane>

            <TabPane tab={<><TagsOutlined /> 自由搭配</>} key="composer">
              <Card
                title="词条自由搭配与抽取"
                extra={
                  <Button size="small" icon={<ReloadOutlined />} onClick={loadCategories} loading={loading.categories}>
                    刷新词库
                  </Button>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    直接查看原词库小类，选择目标后随机抽取词条，可用于拼装自定义预设或测试提示词。
                  </Paragraph>
                  <Select
                    mode="multiple"
                    allowClear
                    showSearch
                    style={{ width: '100%' }}
                    placeholder="选择要抽取的分类（支持小类路径，如 appearance.hairstyle.female_long）"
                    options={categoryOptions}
                    value={selectedCategories}
                    onChange={(values) => {
                      setSelectedCategories(values)
                      setSampleResult({})
                    }}
                    maxTagCount="responsive"
                  />

                  {selectedCategories.length > 0 && (
                    <List
                      size="small"
                      bordered
                      dataSource={selectedCategories}
                      renderItem={(path) => {
                        const category = categories.find((c) => c.path === path)
                        const pickCount = pickOverrides[path] ?? category?.pick_count ?? 1
                        return (
                          <List.Item
                            actions={[
                              <InputNumber
                                size="small"
                                min={1}
                                max={5}
                                value={pickCount}
                                onChange={(value) => setPickOverrides((prev) => ({ ...prev, [path]: value || 1 }))}
                              />,
                              <Button
                                type="link"
                                size="small"
                                icon={<CloseOutlined />}
                                onClick={() => {
                                  setSelectedCategories((prev) => prev.filter((p) => p !== path))
                                  setSampleResult({})
                                }}
                              >
                                移除
                              </Button>
                            ]}
                          >
                            <List.Item.Meta
                              title={
                                <Space>
                                  <Text strong>{category?.name || path}</Text>
                                  {category?.is_builtin && <Tag color="blue">内置</Tag>}
                                  <Text code style={{ fontSize: 12 }}>{path}</Text>
                                </Space>
                              }
                              description={`词条数: ${category?.items?.length ?? 0} | 抽取数量: ${pickCount}`}
                            />
                          </List.Item>
                        )
                      }}
                    />
                  )}

                  <Space>
                    <Button
                      type="primary"
                      icon={<ThunderboltOutlined />}
                      loading={loading.sampling}
                      onClick={handleSampleWords}
                    >
                      抽取词条
                    </Button>
                    <Button
                      icon={<SaveOutlined />}
                      onClick={handleAppendSampleToPrompt}
                      disabled={!Object.keys(sampleResult).length}
                    >
                      填入测试区
                    </Button>
                    <Button
                      icon={<CloseOutlined />}
                      onClick={() => setSampleResult({})}
                      disabled={!Object.keys(sampleResult).length}
                    >
                      清空结果
                    </Button>
                  </Space>

                  {Object.keys(sampleResult).length > 0 && (
                    <Card size="small" type="inner" title="抽取结果">
                      {Object.entries(sampleResult).map(([path, words]) => (
                        <div key={path} style={{ marginBottom: 8 }}>
                          <Text strong>{path}</Text>
                          <Space wrap style={{ marginLeft: 8 }}>
                            {words.map((word, idx) => (
                              <Tag key={`${path}-${idx}`} color="blue">
                                {word}
                              </Tag>
                            ))}
                          </Space>
                        </div>
                      ))}
                    </Card>
                  )}
                </Space>
              </Card>
            </TabPane>

            {/* 增强预览标签页 */}
            <TabPane tab={<><EyeOutlined /> 增强预览</>} key="preview">
              <Card
                title="提示词增强预览"
                extra={
                  <Button icon={<EyeOutlined />} type="primary" loading={loading.preview} onClick={previewEnhancement}>
                    生成预览
                  </Button>
                }
              >
                <TextArea
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  rows={3}
                  placeholder="输入提示词测试增强效果"
                />

                {preview && (
                  <>
                    <Divider />
                    <Paragraph><Text strong>增强后：</Text></Paragraph>
                    <div style={{ background: '#f7f9fb', borderRadius: 8, padding: 12, lineHeight: 1.6 }}>
                      {preview.enhanced}
                    </div>
                    <Space wrap style={{ marginTop: 12 }}>
                      <Tag color={preview.is_enhanced ? 'blue' : 'default'}>
                        {preview.is_enhanced ? '已增强' : '未修改'}
                      </Tag>
                      {Object.entries(preview.intents).map(([key, value]) => (
                        <Tag key={key} color={value ? 'green' : 'default'}>
                          {key}: {value ? '是' : '否'}
                        </Tag>
                      ))}
                    </Space>
                  </>
                )}
              </Card>
            </TabPane>
          </Tabs>
        </Col>
      </Row>

      {/* 新建/编辑意图模态框 */}
      <Modal
        title={editingIntent ? '编辑意图' : '新增意图'}
        open={intentModalVisible}
        onCancel={() => {
          setIntentModalVisible(false)
          setEditingIntent(null)
          intentForm.resetFields()
          setIntentCategorySelection([])
          setIntentPickOverrides({})
        }}
        onOk={() => intentForm.submit()}
      >
        <Form form={intentForm} onFinish={handleSaveIntent} layout="vertical">
          <Form.Item
            name="name"
            label="意图名称"
            rules={[{ required: true, message: '请输入唯一名称' }]}
          >
            <Input placeholder="如 portrait 或 landscape" disabled={!!editingIntent} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input placeholder="简要说明触发场景" />
          </Form.Item>
          <Form.Item
            name="keywords"
            label="关键词（逗号或换行分隔）"
            rules={[{ required: true, message: '请输入关键词' }]}
          >
            <TextArea rows={4} placeholder="如 自拍, 人像, portrait" />
          </Form.Item>
          <Form.Item label="增强分类">
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="选择命中该意图时要增强的分类"
              options={categoryOptions}
              value={intentCategorySelection}
              onChange={(values) => setIntentCategorySelection(values)}
              maxTagCount="responsive"
            />
            {intentCategorySelection.length > 0 && (
              <List
                size="small"
                dataSource={intentCategorySelection}
                style={{ marginTop: 8 }}
                renderItem={(path) => {
                  const category = categories.find((c) => c.path === path)
                  const pickCount = intentPickOverrides[path] ?? category?.pick_count ?? 1
                  return (
                    <List.Item
                      actions={[
                        <InputNumber
                          size="small"
                          min={1}
                          max={5}
                          value={pickCount}
                          onChange={(value) =>
                            setIntentPickOverrides((prev) => ({ ...prev, [path]: value || 1 }))
                          }
                        />
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <Text strong>{category?.name || path}</Text>
                            {category?.is_builtin && <Tag color="blue">内置</Tag>}
                            <Text code style={{ fontSize: 12 }}>{path}</Text>
                          </Space>
                        }
                        description={`抽取数量: ${pickCount} | 词条数 ${category?.items?.length ?? 0}`}
                      />
                    </List.Item>
                  )
                }}
              />
            )}
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 新建/编辑分类模态框 */}
      <Modal
        title={editingCategory ? '编辑分类' : '新建分类'}
        open={categoryModalVisible}
        onCancel={() => {
          setCategoryModalVisible(false)
          setEditingCategory(null)
          categoryForm.resetFields()
        }}
        onOk={() => categoryForm.submit()}
      >
        <Form form={categoryForm} onFinish={handleCreateCategory} layout="vertical">
          <Form.Item name="path" label="分类路径" rules={[{ required: true }]}>
            <Input placeholder="如: custom.style" disabled={!!editingCategory} />
          </Form.Item>
          <Form.Item name="name" label="显示名称" rules={[{ required: true }]}>
            <Input placeholder="如: 自定义风格" />
          </Form.Item>
          <Form.Item name="pick_count" label="抽取数量" initialValue={1}>
            <InputNumber min={1} max={5} />
          </Form.Item>
          {!editingCategory && (
            <Form.Item name="items" label="初始词条">
              <TextArea rows={4} placeholder="每行一个词条" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 预设编辑模态框 */}
      <Modal
        title={editingPreset ? '编辑预设' : '新建预设'}
        open={presetModalVisible}
        onCancel={() => {
          setPresetModalVisible(false)
          setEditingPreset(null)
          setPresetCategorySelection([])
          setPresetPickOverrides({})
          presetForm.resetFields()
        }}
        onOk={() => presetForm.submit()}
      >
        <Form form={presetForm} onFinish={handleSavePreset} layout="vertical">
          <Form.Item name="name" label="预设名称" rules={[{ required: true }]}>
            <Input placeholder="如: casual_cute" disabled={!!editingPreset} />
          </Form.Item>
          <Form.Item name="description" label="描述" rules={[{ required: true }]}>
            <Input placeholder="如: 休闲可爱" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
          <Form.Item label="抽取分类">
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="选择要抽取的大类或具体路径"
              options={categoryOptions}
              value={presetCategorySelection}
              onChange={(values) => setPresetCategorySelection(values)}
              maxTagCount="responsive"
            />
            {presetCategorySelection.length > 0 && (
              <List
                size="small"
                dataSource={presetCategorySelection}
                style={{ marginTop: 8 }}
                renderItem={(path) => {
                  const category = categories.find((c) => c.path === path)
                  const pickCount = presetPickOverrides[path] ?? category?.pick_count ?? 1
                  return (
                    <List.Item
                      actions={[
                        <InputNumber
                          size="small"
                          min={1}
                          max={5}
                          value={pickCount}
                          onChange={(value) => setPresetPickOverrides((prev) => ({ ...prev, [path]: value || 1 }))}
                        />
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <Text strong>{category?.name || path}</Text>
                            {category?.is_builtin && <Tag color="blue">内置</Tag>}
                            <Text code style={{ fontSize: 12 }}>{path}</Text>
                          </Space>
                        }
                        description={`抽取数量: ${pickCount} | 词条数: ${category?.items?.length ?? 0}`}
                      />
                    </List.Item>
                  )
                }}
              />
            )}
          </Form.Item>
          <Form.Item name="outfit_style" label="穿搭风格" initialValue="random">
            <Select>
              <Select.Option value="random">随机</Select.Option>
              <Select.Option value="casual">休闲</Select.Option>
              <Select.Option value="formal">正式</Select.Option>
              <Select.Option value="cute">可爱</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="scene_type" label="场景类型" initialValue="random">
            <Select>
              <Select.Option value="random">随机</Select.Option>
              <Select.Option value="indoor">室内</Select.Option>
              <Select.Option value="outdoor">室外</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加词条模态框 */}
      <Modal
        title="添加词条"
        open={wordModalVisible}
        onCancel={() => {
          setWordModalVisible(false)
          wordForm.resetFields()
        }}
        onOk={() => wordForm.submit()}
      >
        <Form form={wordForm} onFinish={handleAddWords} layout="vertical">
          <Form.Item label="目标分类">
            <Input value={selectedCategory} disabled />
          </Form.Item>
          <Form.Item name="words" label="词条列表" rules={[{ required: true }]}>
            <TextArea rows={6} placeholder="每行一个词条" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default PromptEnhancerPage
