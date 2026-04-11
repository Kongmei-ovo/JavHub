from __future__ import annotations
from typing import Optional, TypedDict


class MagnetInfo(TypedDict):
    """磁力链接信息"""
    magnet: str
    title: str
    size: str
    quality: Optional[str]
    resolution: Optional[str]
    hd: bool
    subtitle: bool


class MovieDetail(TypedDict):
    """影片详情"""
    content_id: str
    dvd_id: Optional[str]
    title_ja: Optional[str]
    title_en: Optional[str]
    release_date: Optional[str]
    runtime_mins: Optional[int]
    maker: Optional[dict]
    label: Optional[dict]
    series: Optional[dict]
    categories: list[dict]
    actresses: list[dict]
    magnets: list[MagnetInfo]
    jacket_thumb_url: Optional[str]
    jacket_full_url: Optional[str]