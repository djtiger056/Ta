import React, { useEffect, useState } from 'react'
import {
  Card,
  Form,
  Switch,
  Button,
  Space,
  Row,
  Col,
  message,
  Divider,
  Table,
  Tag,
  Typography,
  Alert,
  Select,
  InputNumber,
} from 'antd'
import { SaveOutlined, ReloadOutlined, ClockCircleOutlined, CheckOutlined, StopOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

type ReminderConfig = {
  enabled?: boolean
  timezone?: string
  auto_detect?: boolean
  default_delay_minutes?: number
  time_patterns?: {
    tonight?: string
    tomorrow_morning?: string
    tomorrow_noon?: string
    tomorrow_evening?: string
  }
}

type ReminderItem = {
  id: number
  user_id: string
  session_id: string
  content: string
  trigger_time: string
  status: string
  original_message?: string
  time_expression?: string
  reminder_message?: string
  created_at: string
  completed_at?: string
}

const ReminderPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [remindersLoading, setRemindersLoading] = useState(false)
  const [config, setConfig] = useState<ReminderConfig>({})
  const [reminders, setReminders] = useState<ReminderItem[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    loadConfig()
    loadReminders()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/reminder/config')
      const data = await response.json()
      if (data.success) {
        setConfig(data.config || {})
        form.setFieldsValue(data.config || {})
      }
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  const loadReminders = async () => {
    try {
      setRemindersLoading(true)
      const response = await fetch('/api/reminder/list?limit=100')
      const data = await response.json()
      if (data.success) {
        setReminders(data.data || [])
      }
    } catch (error) {
      message.error('加载待办事项失败')
    } finally {
      setRemindersLoading(false)
    }
  }

  const saveConfig = async (values: any) => {
    try {
      setLoading(true)
      const response = await fetch('/api/reminder/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      const data = await response.json()
      if (data.success) {
        message.success('配置已保存')
        setConfig(data.config || {})
      } else {
        message.error('保存配置失败')
      }
    } catch (error) {
      message.error('保存配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleReminderAction = async (reminderId: number, action: string) => {
    try {
      const response = await fetch(`/api/reminder/${reminderId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      const data = await response.json()
      if (data.success) {
        message.success(data.message)
        loadReminders()
      } else {
        message.error('操作失败')
      }
    } catch (error) {
      message.error('操作失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '时间表达式',
      dataIndex: 'time_expression',
      key: 'time_expression',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '触发时间',
      dataIndex: 'trigger_time',
      key: 'trigger_time',
      width: 180,
      render: (text: string) => {
        if (!text) return '-'
        const date = new Date(text)
        return date.toLocaleString('zh-CN')
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          pending: { color: 'orange', text: '待处理' },
          completed: { color: 'green', text: '已完成' },
          cancelled: { color: 'red', text: '已取消' },
        }
        const config = statusMap[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => {
        if (!text) return '-'
        const date = new Date(text)
        return date.toLocaleString('zh-CN')
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: ReminderItem) => (
        <Space size="small">
          {record.status === 'pending' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleReminderAction(record.id, 'complete')}
              >
                完成
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleReminderAction(record.id, 'cancel')}
              >
                取消
              </Button>
            </>
          )}
          {record.status !== 'pending' && <Text type="secondary">无操作</Text>}
        </Space>
      ),
    },
  ]

  const filteredReminders = reminders.filter(item => {
    if (statusFilter === 'all') return true
    return item.status === statusFilter
  })

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <Title level={2}>
        <ClockCircleOutlined /> 待办事项配置
      </Title>

      <Alert
        message="待办事项功能说明"
        description="AI会自动检测用户的提醒指令（如'晚点叫我起床'），创建待办事项，并在指定时间主动发送提醒消息。用户回复后，待办事项会自动标记为已完成。"
        type="info"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      <Card title="基本配置" style={{ marginBottom: '24px' }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={saveConfig}
          initialValues={config}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="启用待办事项功能"
                name="enabled"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="时区"
                name="timezone"
              >
                <Select>
                  <Select.Option value="Asia/Shanghai">Asia/Shanghai (中国标准时间)</Select.Option>
                  <Select.Option value="Asia/Tokyo">Asia/Tokyo (日本标准时间)</Select.Option>
                  <Select.Option value="America/New_York">America/New_York (美国东部时间)</Select.Option>
                  <Select.Option value="Europe/London">Europe/London (格林威治标准时间)</Select.Option>
                  <Select.Option value="UTC">UTC (协调世界时)</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="自动检测意图"
                name="auto_detect"
                valuePropName="checked"
                tooltip="启用后，AI会自动检测用户消息中的待办事项意图"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="默认延迟时间（分钟）"
                name="default_delay_minutes"
                tooltip="当无法识别明确时间时，默认延迟的分钟数"
              >
                <InputNumber min={1} max={1440} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
                保存配置
              </Button>
              <Button icon={<ReloadOutlined />} onClick={loadConfig}>
                重新加载
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title={
          <Space>
            <span>待办事项列表</span>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部</Select.Option>
              <Select.Option value="pending">待处理</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="cancelled">已取消</Select.Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadReminders} loading={remindersLoading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredReminders}
          rowKey="id"
          loading={remindersLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  )
}

export default ReminderPage