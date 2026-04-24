import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Form, 
  Input, 
  DatePicker, 
  Button, 
  message, 
  Table, 
  Space,
  Select,
  Tag,
  Modal,
  Statistic,
  Row,
  Col
} from 'antd'
import { 
  PlusOutlined, 
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { reminderApi } from '@/services/api'

const { TextArea } = Input
interface ReminderItem {
  id: number
  user_id: string
  session_id: string
  content: string
  trigger_time: string
  status: string
  original_message?: string
  time_expression?: string
  reminder_message?: string
  metadata?: any
  created_at?: string
  completed_at?: string
}

const ReminderManagePage: React.FC = () => {
  const [form] = Form.useForm()
  const [reminders, setReminders] = useState<ReminderItem[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [userId, setUserId] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [stats, setStats] = useState({ pending: 0, completed: 0, cancelled: 0 })

  useEffect(() => {
    loadReminders()
  }, [userId, statusFilter])

  const loadReminders = async () => {
    if (!userId) {
      setReminders([])
      return
    }
    try {
      setLoading(true)
      const status = statusFilter === 'all' ? undefined : statusFilter
      const data = await reminderApi.getReminderList({ user_id: userId, status, limit: 100 })
      setReminders(data.data || [])
      
      // 计算统计
      const pending = (data.data || []).filter((r: ReminderItem) => r.status === 'pending').length
      const completed = (data.data || []).filter((r: ReminderItem) => r.status === 'completed').length
      const cancelled = (data.data || []).filter((r: ReminderItem) => r.status === 'cancelled').length
      setStats({ pending, completed, cancelled })
    } catch (error) {
      console.error('加载待办事项失败:', error)
      message.error('加载待办事项失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      const triggerTime = values.trigger_time.format('YYYY-MM-DD HH:mm:ss')
      
      await reminderApi.createReminder({
        user_id: values.user_id || userId,
        session_id: values.session_id || userId,
        content: values.content,
        trigger_time: triggerTime,
        time_expression: values.time_expression,
        reminder_message: values.reminder_message,
        metadata: {}
      })
      
      message.success('待办事项创建成功')
      setModalVisible(false)
      form.resetFields()
      await loadReminders()
    } catch (error) {
      console.error('创建待办事项失败:', error)
      message.error('创建待办事项失败')
    }
  }

  const handleAction = async (id: number, action: 'complete' | 'cancel') => {
    try {
      await reminderApi.reminderAction(id, action)
      message.success(action === 'complete' ? '待办事项已完成' : '待办事项已取消')
      await loadReminders()
    } catch (error) {
      console.error('执行操作失败:', error)
      message.error('执行操作失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '触发时间',
      dataIndex: 'trigger_time',
      key: 'trigger_time',
      width: 180,
      render: (time: string) => {
        if (!time) return '-'
        const date = new Date(time)
        return date.toLocaleString('zh-CN')
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap = {
          pending: { color: 'blue', text: '待处理', icon: <ClockCircleOutlined /> },
          completed: { color: 'green', text: '已完成', icon: <CheckCircleOutlined /> },
          cancelled: { color: 'red', text: '已取消', icon: <CloseCircleOutlined /> },
        }
        const config = statusMap[status as keyof typeof statusMap] || statusMap.pending
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        )
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => {
        if (!time) return '-'
        const date = new Date(time)
        return date.toLocaleString('zh-CN')
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: ReminderItem) => (
        <Space>
          {record.status === 'pending' && (
            <>
              <Button 
                type="link" 
                size="small"
                onClick={() => handleAction(record.id, 'complete')}
              >
                完成
              </Button>
              <Button 
                type="link" 
                danger
                size="small"
                onClick={() => handleAction(record.id, 'cancel')}
              >
                取消
              </Button>
            </>
          )}
          {record.status === 'completed' && (
            <Tag color="green">已完成</Tag>
          )}
          {record.status === 'cancelled' && (
            <Tag color="red">已取消</Tag>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic 
              title="待处理" 
              value={stats.pending} 
              valueStyle={{ color: '#1890ff' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic 
              title="已完成" 
              value={stats.completed} 
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic 
              title="已取消" 
              value={stats.cancelled} 
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="待办事项管理">
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="输入用户ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ width: 200 }}
          />
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
          <Button type="primary" icon={<ReloadOutlined />} onClick={loadReminders} loading={loading}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            创建待办事项
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={reminders}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          loading={loading}
        />
      </Card>

      <Modal
        title="创建待办事项"
        open={modalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="用户ID"
            name="user_id"
            initialValue={userId}
            rules={[{ required: true, message: '请输入用户ID' }]}
          >
            <Input placeholder="用户ID" />
          </Form.Item>
          <Form.Item
            label="会话ID"
            name="session_id"
            initialValue={userId}
          >
            <Input placeholder="会话ID（可选）" />
          </Form.Item>
          <Form.Item
            label="待办事项内容"
            name="content"
            rules={[{ required: true, message: '请输入待办事项内容' }]}
          >
            <TextArea rows={4} placeholder="例如：晚上8点提醒我吃饭" />
          </Form.Item>
          <Form.Item
            label="触发时间"
            name="trigger_time"
            rules={[{ required: true, message: '请选择触发时间' }]}
          >
            <DatePicker 
              showTime 
              format="YYYY-MM-DD HH:mm:ss" 
              style={{ width: '100%' }}
              placeholder="选择触发时间"
            />
          </Form.Item>
          <Form.Item
            label="时间表达式"
            name="time_expression"
          >
            <Input placeholder="例如：今晚、明早" />
          </Form.Item>
          <Form.Item
            label="提醒消息"
            name="reminder_message"
          >
            <TextArea rows={2} placeholder="自定义提醒消息（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ReminderManagePage
