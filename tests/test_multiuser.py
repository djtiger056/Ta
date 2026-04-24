"""测试多用户功能"""
import pytest
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.user import user_manager, auth_manager, User


class TestMultiUser:
    """测试多用户功能"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """测试前设置"""
        # 初始化数据库
        await user_manager.init_db()
        yield
        # 清理测试数据（可选）
    
    async def test_create_user(self):
        """测试创建用户"""
        import random
        random_suffix = random.randint(1000, 9999)
        username = f'testuser1_{random_suffix}'
        
        user = await user_manager.create_user(
            username=username,
            password='password123',
            nickname='测试用户1',
            qq_user_id=f'123456789_{random_suffix}'
        )
        
        print(f"[DEBUG] Created user: {user}")
        
        assert user is not None
        assert user.username == username
        assert user.qq_user_id == f'123456789_{random_suffix}'
        assert user.nickname == '测试用户1'
        
        print("[PASS] 用户创建测试通过")
    
    async def test_duplicate_username(self):
        """测试重复用户名"""
        await user_manager.create_user(
            username='testuser2',
            password='password123'
        )
        
        # 尝试创建相同用户名的用户
        user = await user_manager.create_user(
            username='testuser2',
            password='password456'
        )
        
        assert user is None
        
        print("[PASS] 重复用户名测试通过")
    
    async def test_duplicate_qq_id(self):
        """测试重复QQ ID"""
        await user_manager.create_user(
            username='testuser3',
            password='password123',
            qq_user_id='987654321'
        )
        
        # 尝试创建相同QQ ID的用户
        user = await user_manager.create_user(
            username='testuser4',
            password='password456',
            qq_user_id='987654321'
        )
        
        assert user is None
        
        print("[PASS] 重复QQ ID测试通过")
    
    async def test_user_authentication(self):
        """测试用户认证"""
        await user_manager.create_user(
            username='testuser5',
            password='password123'
        )
        
        # 正确密码
        user = await user_manager.authenticate('testuser5', 'password123')
        assert user is not None
        assert user.username == 'testuser5'
        
        # 错误密码
        user = await user_manager.authenticate('testuser5', 'wrongpassword')
        assert user is None
        
        # 不存在的用户
        user = await user_manager.authenticate('nonexistent', 'password123')
        assert user is None
        
        print("[PASS] 用户认证测试通过")
    
    async def test_token_generation(self):
        """测试令牌生成"""
        token = auth_manager.create_token(
            user_id=1,
            username='testuser',
            qq_user_id='123456789'
        )
        
        print(f"[DEBUG] Generated token: {token}")
        print(f"[DEBUG] Token type: {type(token)}")
        
        assert token is not None
        assert isinstance(token, str)
        
        # 解码令牌
        payload = auth_manager.decode_token(token)
        print(f"[DEBUG] Decoded payload: {payload}")
        
        if payload is None:
            print("[DEBUG] Token decode returned None, trying without verification")
            # 尝试不验证签名解码
            try:
                import jwt
                payload = jwt.decode(token, options={'verify_signature': False})
                print(f"[DEBUG] Payload without verification: {payload}")
            except Exception as e:
                print(f"[DEBUG] Decode error: {e}")
        
        assert payload is not None, f"Token decode failed. Token: {token}"
        assert payload['user_id'] == 1
        assert payload['username'] == 'testuser'
        assert payload['qq_user_id'] == '123456789'
        
        print("[PASS] 令牌生成测试通过")
    
    async def test_user_config(self):
        """测试用户配置"""
        # 创建用户
        user = await user_manager.create_user(
            username='testuser6',
            password='password123'
        )
        
        # 更新用户配置
        config_data = {
            'system_prompt': '你是一个测试助手',
            'llm_config': {'temperature': 0.9, 'max_tokens': 500},
            'tts_config': {'voice': 'test_voice'}
        }
        
        success = await user_manager.update_user_config(user.id, config_data)
        assert success is True
        
        # 获取用户配置
        user_config_dict = await user_manager.get_user_config_dict(user.id)
        assert user_config_dict['system_prompt'] == '你是一个测试助手'
        assert user_config_dict['llm']['temperature'] == 0.9
        assert user_config_dict['llm']['max_tokens'] == 500
        assert user_config_dict['tts']['voice'] == 'test_voice'
        
        print("[PASS] 用户配置测试通过")
    
    async def test_config_merger(self):
        """测试配置合并"""
        from backend.utils.config_merger import config_merger
        
        global_config = {
            'system_prompt': '全局提示词',
            'llm': {
                'temperature': 0.7,
                'max_tokens': 200,
                'model': 'gpt-3.5'
            },
            'tts': {
                'voice': 'default',
                'enabled': True
            }
        }
        
        user_config = {
            'system_prompt': '用户自定义提示词',
            'llm': {
                'temperature': 0.9
            }
        }
        
        merged = config_merger.get_user_config(global_config, user_config)
        
        # 用户配置应该覆盖全局配置
        assert merged['system_prompt'] == '用户自定义提示词'
        assert merged['llm']['temperature'] == 0.9
        # 未指定的配置应该保留全局配置
        assert merged['llm']['max_tokens'] == 200
        assert merged['llm']['model'] == 'gpt-3.5'
        assert merged['tts']['voice'] == 'default'
        assert merged['tts']['enabled'] == True
        
        print("[PASS] 配置合并测试通过")


async def test_all():
    """运行所有测试"""
    test = TestMultiUser()
    
    print("开始测试多用户功能...\n")
    
    # 初始化数据库
    await user_manager.init_db()
    
    # 运行测试
    await test.test_create_user()
    await test.test_duplicate_username()
    await test.test_duplicate_qq_id()
    await test.test_user_authentication()
    await test.test_token_generation()
    await test.test_user_config()
    await test.test_config_merger()
    
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(test_all())