"""
基础智能体抽象类
提供智能体的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agent.{name}")
        self.context = {}
    
    @abstractmethod
    async def process(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """处理用户查询的核心方法"""
        pass
    
    async def validate_input(self, **kwargs) -> bool:
        """输入验证"""
        return True
    
    def update_context(self, key: str, value: Any):
        """更新上下文"""
        self.context[key] = value
    
    def get_capabilities(self) -> Dict[str, str]:
        """返回智能体的能力描述"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        }