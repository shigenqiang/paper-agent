import React from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { Layout, Menu, Button, Dropdown, Space } from 'antd'
import {
  HomeOutlined,
  EditOutlined,
  BookOutlined,
  SettingOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { usePaperStore } from '../../store/paperStore'

const { Header, Sider, Content } = Layout

const MainLayout = () => {
  const navigate = useNavigate()
  const { sidebarCollapsed, toggleSidebar, theme, setTheme } = usePaperStore()

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/writing',
      icon: <EditOutlined />,
      label: '写作',
    },
    {
      key: '/literature',
      icon: <BookOutlined />,
      label: '文献',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  const themeMenuItems = [
    { key: 'light', label: '亮色模式' },
    { key: 'dark', label: '暗色模式' },
    { key: 'paper', label: '护眼模式' },
  ]

  return (
    <Layout className="min-h-screen">
      <Sider
        trigger={null}
        collapsible
        collapsed={sidebarCollapsed}
        className="!bg-white"
      >
        <div className="h-16 flex items-center justify-center border-b border-gray-200">
          {sidebarCollapsed ? (
            <span className="text-xl font-bold text-primary">PA</span>
          ) : (
            <span className="text-xl font-bold text-primary">Paper Agent</span>
          )}
        </div>
        <Menu
          mode="inline"
          defaultSelectedKeys={['/']}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="border-r-0"
        />
      </Sider>

      <Layout>
        <Header className="bg-white !px-4 flex items-center justify-between border-b border-gray-200">
          <Space>
            <Button
              type="text"
              icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleSidebar}
            />
          </Space>

          <Space>
            <Dropdown
              menu={{
                items: themeMenuItems,
                onClick: ({ key }) => setTheme(key)
              }}
              placement="bottomRight"
            >
              <Button type="text">{theme === 'light' ? '☀️' : theme === 'dark' ? '🌙' : '📖'}</Button>
            </Dropdown>

            <Dropdown
              menu={{
                items: [
                  { key: 'profile', label: '个人中心' },
                  { key: 'help', label: '帮助文档' },
                  { type: 'divider' },
                  { key: 'logout', label: '退出登录' },
                ]
              }}
              placement="bottomRight"
            >
              <Button type="text" icon={<UserOutlined />} />
            </Dropdown>
          </Space>
        </Header>

        <Content className="!p-6 bg-gray-50">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout