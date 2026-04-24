"""用户和用户配置数据模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from backend.utils.datetime_utils import get_now

Base = declarative_base()


def get_current_time():
    """获取当前时间供SQLAlchemy使用"""
    return get_now()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    qq_user_id = Column(String(50), unique=True, nullable=True, index=True)  # QQ用户ID
    nickname = Column(String(50), nullable=True)
    avatar = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1)  # 1: 启用, 0: 禁用
    is_admin = Column(Integer, default=0)  # 1: 管理员, 0: 普通用户
    created_at = Column(DateTime, default=get_current_time, nullable=False)
    updated_at = Column(DateTime, default=get_current_time, onupdate=get_current_time, nullable=False)
    
    # 关联用户配置
    user_config = relationship("UserConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserConfig(Base):
    """用户配置表"""
    __tablename__ = "user_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    # 各模块配置 (JSON格式存储)
    system_prompt = Column(Text, nullable=True)  # 用户自定义系统提示词
    llm_config = Column(Text, nullable=True)  # LLM配置 (JSON)
    tts_config = Column(Text, nullable=True)  # TTS配置 (JSON)
    image_gen_config = Column(Text, nullable=True)  # 图像生成配置 (JSON)
    vision_config = Column(Text, nullable=True)  # 视觉识别配置 (JSON)
    prompt_enhancer_config = Column(Text, nullable=True)  # 提示词增强配置 (JSON)
    emote_config = Column(Text, nullable=True)  # 表情包配置 (JSON)
    proactive_chat_config = Column(Text, nullable=True)  # 主动聊天配置 (JSON)
    
    # 其他用户偏好设置 (JSON格式)
    preferences = Column(Text, nullable=True)  # 其他偏好设置 (JSON)
    
    created_at = Column(DateTime, default=get_current_time, nullable=False)
    updated_at = Column(DateTime, default=get_current_time, onupdate=get_current_time, nullable=False)
    
    # 关联用户
    user = relationship("User", back_populates="user_config")