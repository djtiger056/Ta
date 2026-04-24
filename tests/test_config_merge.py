#!/usr/bin/env python3
"""
测试配置合并逻辑
模拟前端发送不完整的配置，验证深度合并是否保留现有配置
"""

def test_deep_merge():
    """测试_Deep_merge_config方法"""
    
    # 模拟现有的完整配置
    current_config = {
        'enabled': True,
        'provider': 'modelscope',
        'modelscope': {
            'api_key': 'existing-modelscope-key',
            'model': 'Tongyi-MAI/Z-Image-Turbo',
            'timeout': 120
        },
        'yunwu': {
            'api_key': 'existing-yunwu-key',
            'api_base': 'https://yunwu.ai/v1',
            'model': 'jimeng-4.5',
            'timeout': 120
        },
        'trigger_keywords': ['生成图片', '生图'],
        'generating_message': '🎨 正在为你生成图片，请稍候...',
        'error_message': '😢 图片生成失败：{error}',
        'success_message': '✨ 图片已生成完成！'
    }
    
    # 模拟前端发送的配置（切换提供商，但不包含完整的yunwu配置）
    new_config = {
        'enabled': True,
        'provider': 'yunwu',
        'modelscope': {},  # 前端发送空字典
        # yunwu字段可能不存在或为空字典
        'trigger_keywords': ['生成图片', '生图', '看看穿搭', '看照片', '看看', 'ootd'],
        'generating_message': '',
        'error_message': '错误',
        'success_message': '成功'
    }
    
    # 模拟_Deep_merge_config逻辑
    def deep_merge_config(current: dict, new: dict) -> dict:
        """模拟Bot类中的深度合并方法"""
        result = current.copy()
        
        for key, value in new.items():
            if key not in result:
                # 新键，直接添加
                result[key] = value
            elif isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = deep_merge_config(result[key], value)
            elif value is not None and value != "" and value != {} and value != []:
                # 非空值，更新
                result[key] = value
            # 空值保持不变，避免覆盖现有配置
        
        return result
    
    # 测试场景1：前端不发送yunwu字段
    print("=== 测试场景1: 前端不发送yunwu字段 ===")
    test_config1 = new_config.copy()  # 不包含yunwu字段
    
    merged1 = deep_merge_config(current_config, test_config1)
    print(f"原始yunwu配置: {current_config.get('yunwu', '不存在')}")
    print(f"合并后yunwu配置: {merged1.get('yunwu', '不存在')}")
    print(f"modelscope配置是否被清空: {merged1.get('modelscope') == {}}")
    print(f"provider是否正确切换: {merged1.get('provider')}")
    assert merged1.get('yunwu') == current_config['yunwu'], "yunwu配置应该被保留"
    assert merged1.get('modelscope') == current_config['modelscope'], "modelscope配置应该被保留（新值为空字典）"
    assert merged1.get('provider') == 'yunwu', "provider应该切换为yunwu"
    print("测试1通过")
    
    # 测试场景2：前端发送yunwu空字典
    print("\n=== 测试场景2: 前端发送yunwu空字典 ===")
    test_config2 = new_config.copy()
    test_config2['yunwu'] = {}  # 前端发送空字典
    
    merged2 = deep_merge_config(current_config, test_config2)
    print(f"合并后yunwu配置: {merged2.get('yunwu', '不存在')}")
    print(f"yunwu api_key是否保留: {'api_key' in merged2.get('yunwu', {})}")
    assert merged2.get('yunwu') == current_config['yunwu'], "yunwu配置应该被保留（新值为空字典）"
    print("测试2通过")
    
    # 测试场景3：前端发送部分yunwu配置
    print("\n=== 测试场景3: 前端发送部分yunwu配置（只更新model） ===")
    test_config3 = new_config.copy()
    test_config3['yunwu'] = {
        'model': 'jimeng-4.0'  # 只更新model字段
    }
    
    merged3 = deep_merge_config(current_config, test_config3)
    print(f"合并后yunwu配置: {merged3.get('yunwu', '不存在')}")
    print(f"model是否更新: {merged3.get('yunwu', {}).get('model')}")
    print(f"api_key是否保留: {merged3.get('yunwu', {}).get('api_key')}")
    assert merged3.get('yunwu', {}).get('model') == 'jimeng-4.0', "model应该被更新"
    assert merged3.get('yunwu', {}).get('api_key') == current_config['yunwu']['api_key'], "api_key应该被保留"
    print("测试3通过")
    
    print("\n所有测试通过！")

if __name__ == "__main__":
    test_deep_merge()
