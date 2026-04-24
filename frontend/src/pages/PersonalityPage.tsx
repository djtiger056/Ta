import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  message, 
  List, 
  Tag, 
  Space,
  Modal,
  Divider
} from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  SaveOutlined,
  UserOutlined 
} from '@ant-design/icons'
import { Personality } from '@/types'

const { TextArea } = Input

const PersonalityPage: React.FC = () => {
  const [form] = Form.useForm()
  const [personalities, setPersonalities] = useState<Personality[]>([])
  const [editingPersonality, setEditingPersonality] = useState<Personality | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadPersonalities()
  }, [])

  const loadPersonalities = () => {
    // 从localStorage加载人格设定
    const saved = localStorage.getItem('lfbot_personalities')
    if (saved) {
      setPersonalities(JSON.parse(saved))
    } else {
      // 默认人格设定
      const defaultPersonalities: Personality[] = [
        {
          name: '友好助手',
          description: '友善、耐心、乐于助人的AI助手',
          system_prompt: '你是一个友好的AI助手，能够与用户进行自然对话。请用简洁、友好的方式回答用户的问题。',
          traits: ['友善', '耐心', '专业']
        },
        {
          name: '幽默伙伴',
          description: '风趣幽默，喜欢开玩笑的聊天伙伴',
          system_prompt: '你是一个幽默风趣的AI伙伴，喜欢用轻松诙谐的方式与用户交流。可以在回答中适当加入一些幽默元素，但要保持有用性。',
          traits: ['幽默', '风趣', '创意']
        },
        {
          name: '专业顾问',
          description: '严谨、专业、注重细节的专家顾问',
          system_prompt: '你是一个专业的AI顾问，提供准确、详细、有深度的回答。请确保信息的准确性，并尽可能提供全面的解释。',
          traits: ['专业', '严谨', '详细']
        }
      ]
      setPersonalities(defaultPersonalities)
      savePersonalities(defaultPersonalities)
    }
  }

  const savePersonalities = (data: Personality[]) => {
    localStorage.setItem('lfbot_personalities', JSON.stringify(data))
  }

  const handleAdd = () => {
    setEditingPersonality(null)
    setModalVisible(true)
    form.resetFields()
  }

  const handleEdit = (personality: Personality) => {
    setEditingPersonality(personality)
    setModalVisible(true)
    form.setFieldsValue(personality)
  }

  const handleDelete = (name: string) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除人格设定"${name}"吗？`,
      onOk: () => {
        const newPersonalities = personalities.filter(p => p.name !== name)
        setPersonalities(newPersonalities)
        savePersonalities(newPersonalities)
        message.success('删除成功')
      }
    })
  }

  const handleModalOk = async () => {
    try {
      setLoading(true)
      const values = await form.validateFields()
      
      // 处理特征标签
      if (values.traits && typeof values.traits === 'string') {
        values.traits = values.traits.split(',').map((t: string) => t.trim()).filter((t: string) => t)
      }
      
      if (editingPersonality) {
        // 编辑现有人格
        const newPersonalities = personalities.map(p => 
          p.name === editingPersonality.name ? { ...values } : p
        )
        setPersonalities(newPersonalities)
        savePersonalities(newPersonalities)
        message.success('更新成功')
      } else {
        // 添加新人格
        if (personalities.some(p => p.name === values.name)) {
          message.error('该人格名称已存在')
          return
        }
        const newPersonalities = [...personalities, values]
        setPersonalities(newPersonalities)
        savePersonalities(newPersonalities)
        message.success('添加成功')
      }
      
      setModalVisible(false)
    } catch (error) {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleApplyPersonality = async (personality: Personality) => {
    try {
      // 这里应该调用API应用人格设定
      // await configApi.updateSystemPrompt(personality.system_prompt)
      message.success(`已应用人格设定: ${personality.name}`)
    } catch (error) {
      message.error('应用人格设定失败')
    }
  }

  return (
    <div>
      <Card 
        title="人格设定管理" 
        extra={
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            添加人格
          </Button>
        }
      >
        <List
          dataSource={personalities}
          renderItem={(personality) => (
            <List.Item
              actions={[
                <Button 
                  key="apply" 
                  type="link" 
                  onClick={() => handleApplyPersonality(personality)}
                >
                  应用
                </Button>,
                <Button 
                  key="edit" 
                  type="link" 
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(personality)}
                >
                  编辑
                </Button>,
                <Button 
                  key="delete" 
                  type="link" 
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(personality.name)}
                >
                  删除
                </Button>
              ]}
            >
              <List.Item.Meta
                avatar={<UserOutlined style={{ fontSize: '24px', color: '#1890ff' }} />}
                title={
                  <Space>
                    {personality.name}
                    {personality.traits.map(trait => (
                      <Tag key={trait} color="blue">{trait}</Tag>
                    ))}
                  </Space>
                }
                description={personality.description}
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal
        title={editingPersonality ? '编辑人格设定' : '添加人格设定'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        confirmLoading={loading}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            label="人格名称"
            name="name"
            rules={[{ required: true, message: '请输入人格名称' }]}
          >
            <Input placeholder="例如: 友好助手" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入人格描述' }]}
          >
            <Input placeholder="简短描述这个人格的特点" />
          </Form.Item>

          <Form.Item
            label="系统提示词"
            name="system_prompt"
            rules={[{ required: true, message: '请输入系统提示词' }]}
          >
            <TextArea
              rows={6}
              placeholder="定义AI角色的详细提示词..."
            />
          </Form.Item>

          <Form.Item
            label="特征标签"
            name="traits"
            help="用逗号分隔多个特征"
          >
            <Input placeholder="例如: 友善,耐心,专业" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default PersonalityPage