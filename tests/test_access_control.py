"""测试用户访问控制功能"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config import config
from backend.adapters.qq import QQAdapter
from backend.core.bot import Bot


class TestAccessControl:
    """测试访问控制功能"""
    
    def test_config_loading(self):
        """测试配置加载"""
        access_config = config.qq_access_control_config
        
        # 验证配置结构
        assert 'enabled' in access_config
        assert 'mode' in access_config
        assert 'whitelist' in access_config
        assert 'blacklist' in access_config
        assert 'deny_message' in access_config
        
        print("[PASS] 配置加载测试通过")
    
    def test_whitelist_mode(self):
        """测试白名单模式"""
        # 创建模拟的 QQ 适配器
        bot = Bot()
        adapter = QQAdapter(bot)
        
        # 设置为白名单模式
        adapter.access_control_enabled = True
        adapter.access_control_mode = 'whitelist'
        adapter.access_whitelist = {'924030299', '123456789'}
        adapter.access_blacklist = set()
        
        # 测试白名单中的用户
        has_access, deny_msg = adapter._check_user_access('924030299')
        assert has_access is True
        assert deny_msg is None
        
        # 测试不在白名单中的用户
        has_access, deny_msg = adapter._check_user_access('999999999')
        assert has_access is False
        assert deny_msg is not None
        
        print("[PASS] 白名单模式测试通过")
    
    def test_blacklist_mode(self):
        """测试黑名单模式"""
        # 创建模拟的 QQ 适配器
        bot = Bot()
        adapter = QQAdapter(bot)
        
        # 设置为黑名单模式
        adapter.access_control_enabled = True
        adapter.access_control_mode = 'blacklist'
        adapter.access_whitelist = set()
        adapter.access_blacklist = {'111111111', '222222222'}
        
        # 测试不在黑名单中的用户
        has_access, deny_msg = adapter._check_user_access('924030299')
        assert has_access is True
        assert deny_msg is None
        
        # 测试黑名单中的用户
        has_access, deny_msg = adapter._check_user_access('111111111')
        assert has_access is False
        assert deny_msg is not None
        
        print("[PASS] 黑名单模式测试通过")
    
    def test_disabled_mode(self):
        """测试关闭模式"""
        # 创建模拟的 QQ 适配器
        bot = Bot()
        adapter = QQAdapter(bot)
        
        # 设置为关闭模式
        adapter.access_control_enabled = True
        adapter.access_control_mode = 'disabled'
        adapter.access_whitelist = set()
        adapter.access_blacklist = set()
        
        # 测试所有用户都应该被允许
        has_access, deny_msg = adapter._check_user_access('924030299')
        assert has_access is True
        assert deny_msg is None
        
        has_access, deny_msg = adapter._check_user_access('999999999')
        assert has_access is True
        assert deny_msg is None
        
        print("[PASS] 关闭模式测试通过")
    
    def test_access_control_disabled(self):
        """测试访问控制完全关闭"""
        # 创建模拟的 QQ 适配器
        bot = Bot()
        adapter = QQAdapter(bot)
        
        # 关闭访问控制
        adapter.access_control_enabled = False
        
        # 测试所有用户都应该被允许
        has_access, deny_msg = adapter._check_user_access('924030299')
        assert has_access is True
        assert deny_msg is None
        
        has_access, deny_msg = adapter._check_user_access('999999999')
        assert has_access is True
        assert deny_msg is None
        
        print("[PASS] 访问控制关闭测试通过")


def test_api_endpoints():
    """测试 API 端点（需要运行服务器）"""
    import httpx
    
    base_url = "http://localhost:8002/api"
    
    try:
        # 测试获取访问控制配置
        response = httpx.get(f"{base_url}/access-control")
        if response.status_code == 200:
            config_data = response.json()
            print(f"[PASS] 获取访问控制配置成功: {config_data}")
        else:
            print(f"[WARN] 获取访问控制配置失败: {response.status_code}")
        
        # 测试更新访问控制配置
        update_data = {
            "enabled": True,
            "mode": "whitelist",
            "whitelist": ["924030299"],
            "blacklist": [],
            "deny_message": "抱歉，你没有权限使用此机器人。"
        }
        response = httpx.put(f"{base_url}/access-control", json=update_data)
        if response.status_code == 200:
            print("[PASS] 更新访问控制配置成功")
        else:
            print(f"[WARN] 更新访问控制配置失败: {response.status_code}")
        
        # 测试获取白名单用户
        response = httpx.get(f"{base_url}/access-control/users?list_type=whitelist")
        if response.status_code == 200:
            users_data = response.json()
            print(f"[PASS] 获取白名单用户成功: {users_data}")
        else:
            print(f"[WARN] 获取白名单用户失败: {response.status_code}")
        
    except httpx.ConnectError:
        print("[WARN] 无法连接到服务器，请确保后端服务正在运行")


if __name__ == "__main__":
    print("开始测试用户访问控制功能...\n")
    
    # 运行单元测试
    test = TestAccessControl()
    test.test_config_loading()
    test.test_whitelist_mode()
    test.test_blacklist_mode()
    test.test_disabled_mode()
    test.test_access_control_disabled()
    
    print("\n单元测试完成！\n")
    
    # 运行 API 测试
    print("开始测试 API 端点...\n")
    test_api_endpoints()
    
    print("\n所有测试完成！")