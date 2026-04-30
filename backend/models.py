from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MagnetInfo(BaseModel):
    """磁力链接信息"""
    title: str
    magnet: str
    size: str
    resolution: str = ""  # 720p/1080p/4K
    hd: bool = False
    subtitle: bool = False  # 是否有字幕


class Movie(BaseModel):
    """统一电影数据模型"""
    # 基础信息
    code: str = ""                    # 番号
    title: str = ""                   # 标题
    actor: str = ""                    # 主演（逗号分隔）
    release_date: str = ""             # 发布日期
    cover_url: str = ""               # 封面图
    backdrop_url: str = ""            # 背景图

    # 详细信息
    genres: List[str] = []            # 类型/标签
    studio: str = ""                   # 制作商
    publisher: str = ""               # 发行商
    duration: int = 0                 # 时长（分钟）

    # 磁力信息（需要单独获取）
    magnets: List[MagnetInfo] = []

    # 剧照/预览图
    samples: List[str] = []

    # 扩展信息
    rating: float = 0.0                # 评分
    source: str = ""                  # 数据来源
    source_url: str = ""              # 原始页面URL
    source_movie_id: str = ""         # 源系统中的ID

    # 演员列表（含头像）
    stars: List[dict] = []            # [{id, name, avatar}]

    # 兼容字段
    date: str = ""                    # 兼容旧版
    images: List[str] = []            # 兼容旧版（samples 别名）


class SearchResult(BaseModel):
    """搜索结果（兼容旧版）"""
    code: str
    title: str
    actor: str
    date: str
    cover_url: str
    magnets: List[MagnetInfo]
    images: List[str] = []


class DownloadTask(BaseModel):
    id: str
    code: str
    title: str
    magnet: str
    path: str
    status: str = "pending"
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class Subscription(BaseModel):
    id: str
    actress_name: str
    actress_id: Optional[int] = None
    enabled: bool = True
    auto_download: bool = False
    last_check: Optional[str] = None
    last_found: Optional[str] = None
    created_at: str


class ConfigUpdate(BaseModel):
    openlist_api_url: Optional[str] = None
    openlist_username: Optional[str] = None
    openlist_password: Optional[str] = None
    openlist_default_path: Optional[str] = None
    emby_api_url: Optional[str] = None
    emby_api_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_allowed_users: Optional[List[str]] = None
    crawler_user_agent: Optional[str] = None
    crawler_request_interval: Optional[int] = None
    scheduler_check_hour: Optional[int] = None
    notification_enabled: Optional[bool] = None
    notification_telegram: Optional[bool] = None


class NotificationConfig(BaseModel):
    enabled: bool = False
    telegram_notify: bool = True
    auto_download_notify: bool = True
    download_complete_notify: bool = True
    new_movie_notify: bool = True


class LogEntry(BaseModel):
    id: int
    level: str
    message: str
    created_at: str
