import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import {
  MessageOutlined,
  SettingOutlined,
  UserOutlined,
  RobotOutlined,
  SoundOutlined,
  PictureOutlined,
  DatabaseOutlined,
  EyeOutlined,
  BellOutlined,
  HighlightOutlined,
  CalendarOutlined,
  SmileOutlined,
  ClockCircleOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import PersonalityPage from './pages/PersonalityPage'
import TTSConfigPage from './pages/TTSConfigPage.tsx'
import ImageGenPage from './pages/ImageGenPage'
import MemoryPage from './pages/MemoryPage'
import VisionPage from './pages/VisionPage'
import ProactiveChatPage from './pages/ProactiveChatPage'
import { useNavigate, useLocation } from 'react-router-dom'
import PromptEnhancerPage from './pages/PromptEnhancerPage'
import DailyHabitsPage from './pages/DailyHabitsPage'
import EmotePage from './pages/EmotePage'
import ReminderPage from './pages/ReminderPage'
import AdminUsersPage from './pages/AdminUsersPage'

const { Header, Sider, Content } = Layout

const App: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: '聊天测试',
    },
    {
      key: '/admin/users',
      icon: <ToolOutlined />,
      label: '多用户配置',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      key: '/personality',
      icon: <UserOutlined />,
      label: '人格设定',
    },
    {
      key: '/tts',
      icon: <SoundOutlined />,
      label: 'TTS配置',
    },
    {
      key: '/image-gen',
      icon: <PictureOutlined />,
      label: '图像生成',
    },
    {
      key: '/prompt-enhancer',
      icon: <HighlightOutlined />,
      label: '提示词增强',
    },
    {
      key: '/emotes',
      icon: <SmileOutlined />,
      label: '表情包管理',
    },
    {
      key: '/daily-habits',
      icon: <CalendarOutlined />,
      label: '每日习惯',
    },
    {
      key: '/memory',
      icon: <DatabaseOutlined />,
      label: '记忆管理',
    },
    {
      key: '/vision',
      icon: <EyeOutlined />,
      label: '视觉识别',
    },
    {
      key: '/proactive',
      icon: <BellOutlined />,
      label: '主动聊天',
    },
    {
      key: '/reminder',
      icon: <ClockCircleOutlined />,
      label: '待办事项',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={200}>
        <div className="logo">
          <RobotOutlined /> LFBot
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          fontSize: '18px',
          fontWeight: 'bold'
        }}>
          LFBot 管理界面
        </Header>
        <Content style={{ margin: '24px 16px 0', overflow: 'auto' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/personality" element={<PersonalityPage />} />
            <Route path="/tts" element={<TTSConfigPage />} />
            <Route path="/image-gen" element={<ImageGenPage />} />
            <Route path="/prompt-enhancer" element={<PromptEnhancerPage />} />
            <Route path="/emotes" element={<EmotePage />} />
            <Route path="/daily-habits" element={<DailyHabitsPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/vision" element={<VisionPage />} />
            <Route path="/proactive" element={<ProactiveChatPage />} />
            <Route path="/reminder" element={<ReminderPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

const AppWrapper: React.FC = () => (
  <Router>
    <App />
  </Router>
)

export default AppWrapper