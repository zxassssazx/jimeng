#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenAI客户端代理解决方案 - 最终版

这个解决方案采用了一种完全不同的方法，完全绕开了原始OpenAI库中的问题。
它不使用继承或复杂的包装，而是提供一个简单的函数，确保在所有情况下都能正确处理代理设置。

使用方法：
1. 导入：from volcano_ai_proxy import create_volcano_ai_client
2. 使用：client = create_volcano_ai_client(api_key, base_url, proxies)
"""

import os
import sys
import httpx
import logging
from typing import Dict, Any, Optional, Union

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入原始OpenAI库
_original_openai_available = False
try:
    from openai import OpenAI as OriginalOpenAI
    from openai import Client as OriginalClient
    _original_openai_available = True
    logger.info(f"成功导入OpenAI库")
except ImportError as e:
    logger.error(f"无法导入OpenAI库: {str(e)}")
    logger.error("请确保已安装OpenAI库: pip install openai")


class VolcanoAIClient:
    """火山AI客户端，专为解决DeepSeek API与OpenAI库v1.3.6的兼容性问题而设计。"""
    
    def __init__(self, api_key: str, base_url: str, http_client: Optional[httpx.Client] = None, **kwargs):
        """初始化火山AI客户端。"""
        self.api_key = api_key
        self.base_url = base_url
        
        # 创建内部OpenAI客户端
        client_kwargs = kwargs.copy()
        
        if http_client:
            client_kwargs['http_client'] = http_client
        
        # 检查OpenAI库是否可用
        if not _original_openai_available:
            raise RuntimeError("OpenAI库不可用，请安装: pip install openai")
        
        # 创建原始客户端
        try:
            # 优先使用Client类
            self.client = OriginalClient(
                api_key=api_key,
                base_url=base_url,
                **client_kwargs
            )
            logger.info("成功创建OriginalClient实例")
        except Exception as e:
            logger.warning(f"创建OriginalClient失败，尝试使用OpenAI类: {str(e)}")
            # 如果失败，尝试使用OpenAI类
            self.client = OriginalOpenAI(
                api_key=api_key,
                base_url=base_url,
                **client_kwargs
            )
            logger.info("成功创建OriginalOpenAI实例")
    
    # 委托所有属性和方法访问到内部客户端
    def __getattr__(self, name: str) -> Any:
        """委托属性和方法访问到内部OpenAI客户端。"""
        return getattr(self.client, name)


# 创建客户端的主函数
def create_volcano_ai_client(
    api_key: str, 
    base_url: str, 
    proxies: Optional[Dict[str, str]] = None,
    **kwargs
) -> VolcanoAIClient:
    """
    创建火山AI客户端，支持代理设置。这是解决DeepSeek API与OpenAI库v1.3.6兼容性问题的推荐方法。
    
    Args:
        api_key (str): API密钥
        base_url (str): API基础URL，例如 "https://api.deepseek.com"
        proxies (dict, optional): 代理配置字典，例如 {'https': 'http://proxy.example.com:8080'}
        **kwargs: 其他传递给OpenAI客户端的参数
        
    Returns:
        VolcanoAIClient: 配置好的火山AI客户端实例
    """
    logger.info(f"创建火山AI客户端: api_key={'已提供' if api_key else '未提供'}, base_url={base_url}, has_proxies={proxies is not None}")
    
    # 创建一个kwargs的副本
    client_kwargs = kwargs.copy()
    http_client = None
    
    # 如果提供了代理配置，创建HTTP客户端
    if proxies:
        logger.info(f"配置代理: {proxies}")
        
        # 从proxies字典中提取一个代理URL（优先使用https）
        proxy_url = proxies.get('https') or proxies.get('http')
        
        if proxy_url:
            logger.info(f"使用代理URL: {proxy_url}")
            
            # 创建自定义的HTTPX客户端，使用正确的proxy参数（单数形式）
            http_client = httpx.Client(
                proxy=proxy_url,
                timeout=client_kwargs.pop('timeout', 60),
                follow_redirects=True
            )
            logger.info("成功创建HTTP客户端")
        else:
            logger.warning("未找到有效的代理URL")
    
    # 创建并返回火山AI客户端
    try:
        return VolcanoAIClient(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
            **client_kwargs
        )
    except Exception as e:
        logger.error(f"创建火山AI客户端失败: {type(e).__name__}: {str(e)}")
        # 清理资源
        if http_client:
            http_client.close()
        raise


# 为了方便用户，提供一个更简单的别名
def create_deepseek_client(
    api_key: str, 
    base_url: str = "https://api.deepseek.com", 
    proxies: Optional[Dict[str, str]] = None,
    **kwargs
) -> VolcanoAIClient:
    """创建DeepSeek API客户端的便捷函数。"""
    return create_volcano_ai_client(api_key, base_url, proxies, **kwargs)


# 简单的测试函数，用于验证功能
def test_client():
    """简单测试函数，用于验证客户端功能。"""
    print("===== 火山AI客户端测试 =====")
    
    # 测试不使用代理
    print("\n测试1: 不使用代理...")
    try:
        client = create_volcano_ai_client(
            api_key="test-api-key",
            base_url="https://api.deepseek.com"
        )
        print("✓ 成功: 创建无代理客户端")
        print(f"客户端类型: {type(client)}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {str(e)}")
    
    # 测试使用代理
    print("\n测试2: 使用代理...")
    try:
        client = create_volcano_ai_client(
            api_key="test-api-key",
            base_url="https://api.deepseek.com",
            proxies={"https": "http://proxy.example.com:8080"}
        )
        print("✓ 成功: 创建带代理客户端")
        print(f"客户端类型: {type(client)}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {str(e)}")
    
    # 测试使用DeepSeek便捷函数
    print("\n测试3: 使用DeepSeek便捷函数...")
    try:
        client = create_deepseek_client(
            api_key="test-api-key",
            proxies={"https": "http://proxy.example.com:8080"}
        )
        print("✓ 成功: 创建DeepSeek客户端")
        print(f"客户端类型: {type(client)}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {str(e)}")
    
    print("\n===== 测试完成 =====")


if __name__ == "__main__":
    # 运行测试
    test_client()
    
    # 提供使用说明
    print("\n\n===== 使用说明 =====")
    print("在您的代码中导入并使用:")
    print("")
    print("# 导入火山AI客户端创建函数")
    print("from volcano_ai_proxy import create_volcano_ai_client")
    print("")
    print("# 创建客户端（不使用代理）")
    print("client = create_volcano_ai_client(")
    print("    api_key='your-api-key',")
    print("    base_url='https://api.deepseek.com'")
    print(")")
    print("")
    print("# 创建客户端（使用代理）")
    print("client = create_volcano_ai_client(")
    print("    api_key='your-api-key',")
    print("    base_url='https://api.deepseek.com',")
    print("    proxies={'https': 'http://proxy.example.com:8080'}")
    print(")")
    print("")
    print("# 使用客户端进行API调用")
    print("# response = client.images.generate(...)")