import React, { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Dropdown, Space, Avatar, Badge, Tooltip, Typography, message } from 'antd'
import {
  HomeOutlined,
  EditOutlined,
  BookOutlined,
  SettingOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  BellOutlined,
  BulbOutlined,
  LeftOutlined,
  RightOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons'
import { usePaperStore } from '../../store/paperStore'

const { Header, Sider, Content } = Layout
const { Text } = Typography

// 主要功能菜单
const MAIN_MENU = [
  {
    key: 'home',
    path: '/',
    icon: <HomeOutlined />,
    label: '工作台',
  },
  {
    key: 'writing',
    path: '/writing',
    icon: <EditOutlined />,
    label: '论文写作',
    badge: null,
  },
  {
    key: 'outline',
    path: '/outline',
    icon: <ThunderboltOutlined />,
    label: '生成大纲',
  },
  {
    key: 'literature',
    path: '/literature',
    icon: <BookOutlined />,
    label: '文献搜索',
  },
  {
    key: 'ai',
    path: '/ai-assistant',
    icon: <RobotOutlined />,
    label: 'AI助手',
  },
  {
    key: 'reports',
    path: '/reports',
    icon: <BulbOutlined />,
    label: '学术资讯',
  },
  {
    key: 'knowledge-graph',
    path: '/knowledge-graph',
    icon: <NodeIndexOutlined />,
    label: '知识图谱',
  },
]

// 快捷操作菜单 - 放在底部
const QUICK_MENU = [
  {
    key: 'features',
    path: '/features',
    icon: <ThunderboltOutlined />,
    label: '功能导航',
  },
  {
    key: 'settings',
    path: '/settings',
    icon: <SettingOutlined />,
    label: '设置中心',
  },
]

const MainLayout = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarCollapsed, toggleSidebar, theme, setTheme } = usePaperStore()
  const [selectedKey, setSelectedKey] = useState(() => {
    const path = location.pathname
    const menu = [...MAIN_MENU, ...QUICK_MENU].find(m => m.path === path)
    return menu?.key || 'home'
  })

  // 用户菜单
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  // 用户菜单
  const handleUserMenu = ({ key }) => {
    if (key === 'help') {
      navigate('/features')
    } else if (key === 'profile') {
      message.info('个人中心暂未开放')
    } else if (key === 'logout') {
      message.success('退出成功')
    }
  }

  // 当路径变化时自动更新选中状态
  useEffect(() => {
    const path = location.pathname
    const menu = [...MAIN_MENU, ...QUICK_MENU].find(m => m.path === path)
    if (menu) {
      setSelectedKey(menu.key)
    }
  }, [location.pathname])

  const handleMenuClick = ({ key }) => {
    const menu = [...MAIN_MENU, ...QUICK_MENU].find(m => m.key === key)
    if (menu) {
      setSelectedKey(key)
      navigate(menu.path)
    }
  }

  const themeMenuItems = [
    { key: 'light', label: '☀️ 亮色模式' },
    { key: 'dark', label: '🌙 暗色模式' },
    { key: 'paper', label: '📖 护眼模式' },
  ]

  const userMenuItems = [
    { key: 'profile', label: '个人中心', icon: <UserOutlined /> },
    { key: 'help', label: '帮助文档', icon: <BookOutlined /> },
    { type: 'divider' },
    { key: 'logout', label: '退出登录', danger: true },
  ]

  return (
    <Layout className="min-h-screen">
      {/* 左侧导航 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={sidebarCollapsed}
        className="!bg-white border-r border-gray-200"
        width={220}
        collapsedWidth={64}
      >
        {/* Logo 区域 */}
        <div className="h-14 flex items-center justify-center border-b border-gray-100">
          {sidebarCollapsed ? (
            <Avatar shape="square" size={32} className="!bg-gradient-to-br from-blue-400 to-blue-600">
              PA
            </Avatar>
          ) : (
            <div className="flex items-center gap-2">
              <Avatar shape="square" size={32} className="!bg-gradient-to-br from-blue-400 to-blue-600">
                PA
              </Avatar>
              <div className="flex flex-col">
                <Text strong className="text-sm leading-tight">Paper Agent</Text>
                <Text type="secondary" className="text-xs leading-tight">智能论文助手</Text>
              </div>
            </div>
          )}
        </div>

        {/* 主导航菜单 */}
        <div className="flex flex-col h-[calc(100vh-56px)]">
          <div className="flex-1 py-2">
            {MAIN_MENU.map(item => (
              <Tooltip
                key={item.key}
                title={sidebarCollapsed ? item.label : ''}
                placement="right"
              >
                <div
                  className={`mx-2 mb-1 px-3 py-2.5 rounded-lg cursor-pointer transition-all flex items-center gap-3 ${
                    selectedKey === item.key
                      ? '!bg-blue-50 text-blue-600'
                      : 'hover:bg-gray-50 text-gray-600'
                  }`}
                  onClick={() => handleMenuClick({ key: item.key })}
                >
                  <span className="text-lg">{item.icon}</span>
                  {!sidebarCollapsed && (
                    <div className="flex-1 flex items-center justify-between">
                      <Text className={`text-sm ${selectedKey === item.key ? 'font-medium' : ''}`}>
                        {item.label}
                      </Text>
                      {item.badge && (
                        <Badge count={item.badge} size="small" />
                      )}
                    </div>
                  )}
                </div>
              </Tooltip>
            ))}
          </div>

          {/* 底部快捷菜单 */}
          <div className="py-2 border-t border-gray-100">
            {QUICK_MENU.map(item => (
              <Tooltip
                key={item.key}
                title={sidebarCollapsed ? item.label : ''}
                placement="right"
              >
                <div
                  className={`mx-2 mb-1 px-3 py-2.5 rounded-lg cursor-pointer transition-all flex items-center gap-3 ${
                    selectedKey === item.key
                      ? '!bg-blue-50 text-blue-600'
                      : 'hover:bg-gray-50 text-gray-600'
                  }`}
                  onClick={() => handleMenuClick({ key: item.key })}
                >
                  <span className="text-lg">{item.icon}</span>
                  {!sidebarCollapsed && (
                    <Text className="text-sm">{item.label}</Text>
                  )}
                </div>
              </Tooltip>
            ))}

            {/* 折叠按钮 */}
            <Tooltip
              title={sidebarCollapsed ? '展开菜单' : '收起菜单'}
              placement="right"
            >
              <div
                className="mx-2 mt-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all flex items-center gap-3 hover:bg-gray-50 text-gray-400"
                onClick={toggleSidebar}
              >
                {sidebarCollapsed ? (
                  <RightOutlined className="text-sm" />
                ) : (
                  <>
                    <LeftOutlined className="text-sm" />
                    <Text className="text-sm">收起菜单</Text>
                  </>
                )}
              </div>
            </Tooltip>
          </div>
        </div>
      </Sider>

      <Layout>
        {/* 顶部 Header */}
        <Header className="!bg-white !px-4 flex items-center justify-between border-b border-gray-200 !h-14">
          <Space>
            <Text type="secondary" className="text-sm">
              {location.pathname === '/' && '欢迎使用智能论文助手'}
              {location.pathname === '/writing' && '论文写作'}
              {location.pathname === '/literature' && '文献管理'}
              {location.pathname === '/ai-assistant' && 'AI助手'}
              {location.pathname === '/reports' && '学术资讯'}
              {location.pathname === '/features' && '功能导航'}
              {location.pathname === '/settings' && '设置中心'}
              {location.pathname === '/knowledge-graph' && '知识图谱'}
            </Text>
          </Space>

          <Space size="middle">
            {/* 通知 */}
            <Button type="text" icon={<BellOutlined />} />

            {/* 主题切换 */}
            <Dropdown
              menu={{
                items: themeMenuItems,
                onClick: ({ key }) => setTheme(key)
              }}
              placement="bottomRight"
            >
              <Button type="text" className="text-lg">
                {theme === 'light' ? '☀️' : theme === 'dark' ? '🌙' : '📖'}
              </Button>
            </Dropdown>

            {/* 用户菜单 */}
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenu,
              }}
              placement="bottomRight"
            >
              <Space className="cursor-pointer">
                <Avatar size="small" className="!bg-blue-500">
                  U
                </Avatar>
                <Text className="text-sm">用户</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 主内容区 */}
        <Content className="!p-4 bg-gray-50 overflow-auto">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
