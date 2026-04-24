import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Divider,
  Form,
  Input,
  Row,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd'
import { DeleteOutlined, FireOutlined, PlusOutlined, ReloadOutlined, SaveOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { dailyHabitsApi } from '@/services/api'
import { DailyHabitSlot, DailyHabitsConfig, DailyHabitsStatus } from '@/types'

const { Title, Text, Paragraph } = Typography

const defaultSlot: DailyHabitSlot = {
  start: '09:00',
  end: '10:00',
  activity: '新的事件',
  desc: '',
}

const DailyHabitsPage: React.FC = () => {
  const [form] = Form.useForm()
  const [schedules, setSchedules] = useState<Record<string, DailyHabitSlot[]>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<DailyHabitsStatus | null>(null)
  const [newScheduleName, setNewScheduleName] = useState('')

  useEffect(() => {
    loadConfig()
    loadStatus()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const cfg = await dailyHabitsApi.getConfig()
      setSchedules(cfg.schedules || {})
      form.setFieldsValue({
        enabled: cfg.enabled,
        timezone: cfg.timezone || '',
        default_schedule: cfg.default_schedule || 'weekday',
        weekend_schedule: cfg.weekend_schedule || '',
        override: {
          enabled: cfg.override?.enabled ?? false,
          activity: cfg.override?.activity || '',
          desc: cfg.override?.desc || '',
          expires_at: cfg.override?.expires_at ? dayjs(cfg.override?.expires_at) : null,
        },
      })
    } catch (err) {
      console.error(err)
      message.error('加载作息配置失败')
    } finally {
      setLoading(false)
    }
  }

  const loadStatus = async () => {
    try {
      const data = await dailyHabitsApi.getStatus()
      setStatus(data)
    } catch (err) {
      console.error(err)
      setStatus(null)
    }
  }

  const upsertSlot = (schedule: string, index: number, field: keyof DailyHabitSlot, value: string) => {
    setSchedules(prev => {
      const copy = { ...prev }
      const slots = copy[schedule] ? [...copy[schedule]] : []
      if (!slots[index]) {
        slots[index] = { ...defaultSlot }
      }
      slots[index] = { ...slots[index], [field]: value }
      copy[schedule] = slots
      return copy
    })
  }

  const addSlot = (schedule: string) => {
    setSchedules(prev => ({
      ...prev,
      [schedule]: [...(prev[schedule] || []), { ...defaultSlot }],
    }))
  }

  const removeSlot = (schedule: string, index: number) => {
    setSchedules(prev => {
      const copy = { ...prev }
      const slots = copy[schedule] ? [...copy[schedule]] : []
      slots.splice(index, 1)
      copy[schedule] = slots
      return copy
    })
  }

  const addSchedule = () => {
    const name = newScheduleName.trim()
    if (!name) {
      message.warning('请输入作息名称')
      return
    }
    setSchedules(prev => {
      if (prev[name]) {
        message.info('已存在同名作息')
        return prev
      }
      return { ...prev, [name]: [{ ...defaultSlot }] }
    })
    setNewScheduleName('')
  }

  const removeSchedule = (name: string) => {
    setSchedules(prev => {
      const next = { ...prev }
      delete next[name]
      if (!Object.keys(next).length) {
        message.warning('至少保留一个作息表')
        return prev
      }
      return next
    })
  }

  const saveConfig = async () => {
    try {
      await form.validateFields()
      if (!Object.keys(schedules).length) {
        message.warning('请至少保留一个作息表')
        return
      }
      setSaving(true)
      const values = form.getFieldsValue()
      const override = values.override || {}
      const expires = override.expires_at as Dayjs | null
      const payload: DailyHabitsConfig = {
        enabled: values.enabled ?? true,
        timezone: values.timezone || null,
        default_schedule: values.default_schedule || 'weekday',
        weekend_schedule: values.weekend_schedule || null,
        override: {
          enabled: override.enabled ?? false,
          activity: override.activity || '',
          desc: override.desc || '',
          expires_at: expires ? expires.toISOString() : null,
        },
        schedules,
      }
      await dailyHabitsApi.saveConfig(payload)
      message.success('已保存并热更新')
      loadStatus()
    } catch (err) {
      console.error(err)
      message.error('保存失败，请检查表单或时间格式')
    } finally {
      setSaving(false)
    }
  }

  const currentScheduleLabels = useMemo(() => {
    if (!status?.status) return []
    const labels: string[] = []
    if (status.status.schedule) labels.push(status.status.schedule)
    if (status.status.source === 'override') labels.push('临时覆盖')
    return labels
  }, [status])

  const renderStatusCard = () => (
    <Card title="当前状态" loading={status === null}>
      {!status?.active && (
        <Alert
          type="info"
          showIcon
          message="尚未匹配到作息段，可能已关闭或时间未覆盖。"
          description="保存配置后会立即生效，无需重启。"
        />
      )}
      {status?.active && status.status && (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space size="small">
            <Tag color="green">{status.status.activity}</Tag>
            {currentScheduleLabels.map(label => (
              <Tag key={label}>{label}</Tag>
            ))}
          </Space>
          <Text>
            {status.status.start && status.status.end
              ? `${status.status.start.slice(11, 16)} - ${status.status.end.slice(11, 16)}`
              : '未设置时间段'}
          </Text>
          {status.status.desc && <Paragraph style={{ marginBottom: 0 }}>{status.status.desc}</Paragraph>}
          {status.context && (
            <Alert
              type="success"
              showIcon
              message="自动注入的上下文"
              description={status.context}
            />
          )}
        </Space>
      )}
    </Card>
  )

  return (
    <div style={{ padding: '0 24px' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            日常作息（MCP）
          </Title>
          <Text type="secondary">前端可视化配置，保存后热更新，无需重启后端。</Text>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadConfig} loading={loading}>
              重新加载
            </Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={saveConfig} loading={saving}>
              保存并热启动
            </Button>
          </Space>
        </Col>
      </Row>

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {renderStatusCard()}

        <Form layout="vertical" form={form}>
          <Card title="基础设置" loading={loading}>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item label="启用 daily_habits" name="enabled" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="时区" name="timezone" tooltip="留空则沿用全局 CLOCK_TIMEZONE 或系统时区">
                  <Input placeholder="Asia/Shanghai 或 UTC+08:00" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="默认作息" name="default_schedule">
                  <Input placeholder="weekday" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="周末作息" name="weekend_schedule">
                  <Input placeholder="weekend" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card
            title={
              <Space>
                <FireOutlined />
                <span>临时状态（快速覆盖）</span>
              </Space>
            }
            loading={loading}
          >
            <Row gutter={16}>
              <Col span={4}>
                <Form.Item label="启用临时状态" name={['override', 'enabled']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="当前活动" name={['override', 'activity']}>
                  <Input placeholder="例：今天临时放假" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="补充描述" name={['override', 'desc']}>
                  <Input placeholder="例：全天都在家，可以随时聊天" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="到期时间" name={['override', 'expires_at']}>
                  <DatePicker showTime style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Alert
              type="info"
              showIcon
              message="开启后将直接覆盖作息表，适合请假/旅行等临时场景。"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Form>

        <Card
          title="作息时间表"
          loading={loading}
          extra={<Text type="secondary">时间格式使用 24 小时制 HH:MM</Text>}
        >
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="新增作息名称（如 weekday / weekend）"
              value={newScheduleName}
              onChange={e => setNewScheduleName(e.target.value)}
              style={{ width: 260 }}
            />
            <Button icon={<PlusOutlined />} type="dashed" onClick={addSchedule}>
              新增作息
            </Button>
          </Space>
          <Divider />
          {!Object.keys(schedules).length && <Text type="secondary">暂无作息，请新增一个时间表。</Text>}
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {Object.entries(schedules).map(([name, slots]) => (
              <Card
                key={name}
                size="small"
                title={
                  <Space>
                    <Text strong>{name}</Text>
                    {name === 'weekday' && <Tag color="blue">默认</Tag>}
                    {name === 'weekend' && <Tag color="purple">周末</Tag>}
                  </Space>
                }
                extra={
                  <Button
                    size="small"
                    icon={<DeleteOutlined />}
                    danger
                    onClick={() => removeSchedule(name)}
                    disabled={Object.keys(schedules).length <= 1}
                  >
                    删除
                  </Button>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  {slots.map((slot, idx) => (
                    <Row gutter={8} align="middle" key={`${name}-${idx}`}>
                      <Col span={4}>
                        <Input
                          value={slot.start}
                          onChange={e => upsertSlot(name, idx, 'start', e.target.value)}
                          placeholder="开始 07:00"
                        />
                      </Col>
                      <Col span={4}>
                        <Input
                          value={slot.end}
                          onChange={e => upsertSlot(name, idx, 'end', e.target.value)}
                          placeholder="结束 09:00"
                        />
                      </Col>
                      <Col span={6}>
                        <Input
                          value={slot.activity}
                          onChange={e => upsertSlot(name, idx, 'activity', e.target.value)}
                          placeholder="活动"
                        />
                      </Col>
                      <Col span={8}>
                        <Input.TextArea
                          value={slot.desc}
                          onChange={e => upsertSlot(name, idx, 'desc', e.target.value)}
                          autoSize
                          placeholder="补充描述"
                        />
                      </Col>
                      <Col span={2}>
                        <Button
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => removeSlot(name, idx)}
                          disabled={slots.length <= 1}
                        />
                      </Col>
                    </Row>
                  ))}
                  <Button type="dashed" icon={<PlusOutlined />} onClick={() => addSlot(name)}>
                    增加时间段
                  </Button>
                </Space>
              </Card>
            ))}
          </Space>
        </Card>
      </Space>
    </div>
  )
}

export default DailyHabitsPage
