"""
Actor avatar service: download from gfriends, crop to 2:3, cache locally.
参考 gfriends-inputer 的下载和图像处理逻辑
"""
import os
import io
import time
import httpx
import hashlib
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from PIL import Image, ImageOps
from config import config

# 缓存目录
AVATAR_CACHE_DIR = Path(__file__).parent.parent / "data" / "avatars"
AVATAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# gfriends 仓库
GFRIENDS_REPO = "https://raw.githubusercontent.com/xinxin8816/gfriends/master"
FILETREE_URL = f"{GFRIENDS_REPO}/Filetree.json"

# 公司优先级（常见大厂优先，DMM系靠后）
COMPANY_PRIORITY = [
    "8-Ideapocket", "7-Madonna", "8-FALENO", "8-SOD", "8-Warashi",
    "8-HNES", "8-GRAPHIS", "9-Javrave", "7-Presitge", "7-M pierre",
    "6-S1", "6-Moodyz", "6-PREMIUM", "6-Affair", "6-HONest",
    "5-Attackers", "5-Kuki", "5-Atom", "5-Das", "5-AVALON",
    "4-Fetish", "4-Kuro", "4-Most", "4-Shingeki",
    "3-Lovepop", "3-MUTEKI", "3-Arrows", "3-Allpro", "3-Happiness",
    "2-Dahlia", "2-Juicy-Honey", "2-Nanairo", "2-Rookie",
    "1-FALENO", "1-Diaz",
    "y-AVDC", "y-Minnano", "y-Sharing", "y-VOP", "y-XXX-AV",
    "z-DMM(骑)", "z-DMM(步)", "z-Derekhsu", "z-Luxu",
]

# 内存缓存
_filetree_cache: Optional[dict] = None
_filetree_cache_time: float = 0
FILETREE_CACHE_TTL = 86400  # 24小时


def _get_filetree() -> dict:
    """获取Filetree，带内存缓存"""
    global _filetree_cache, _filetree_cache_time
    now = time.time()
    if _filetree_cache is not None and now - _filetree_cache_time < FILETREE_CACHE_TTL:
        return _filetree_cache
    try:
        resp = httpx.get(FILETREE_URL, timeout=30, proxies={"http://": None, "https://": None})
        if resp.status_code == 200:
            _filetree_cache = resp.json()
            _filetree_cache_time = now
            return _filetree_cache
    except Exception as e:
        print(f"[avatar] Failed to fetch Filetree: {e}")
    return {}


def _find_best_avatar(name: str, filetree: dict) -> Optional[tuple]:
    """
    根据演员名找最合适的头像文件路径
    返回 (company, filename) 或 None
    """
    content = filetree.get("Content", {})
    name_clean = name.strip()

    # 1. 精确匹配文件名（不含扩展名）
    candidates = []
    for company, files in content.items():
        for filename in files.keys():
            fname_without_ext = filename.rsplit(".", 1)[0]
            if fname_without_ext == name_clean:
                # 记录优先级
                try:
                    priority = COMPANY_PRIORITY.index(company)
                except ValueError:
                    priority = 99
                candidates.append((priority, company, filename))

    if candidates:
        # 取优先级最高的
        candidates.sort(key=lambda x: x[0])
        _, company, filename = candidates[0]
        return company, filename

    # 2. 模糊匹配（包含）
    candidates = []
    for company, files in content.items():
        for filename in files.keys():
            fname_without_ext = filename.rsplit(".", 1)[0]
            if name_clean in fname_without_ext or fname_without_ext in name_clean:
                try:
                    priority = COMPANY_PRIORITY.index(company)
                except ValueError:
                    priority = 99
                candidates.append((priority, company, filename))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        _, company, filename = candidates[0]
        return company, filename

    return None


def _download_raw(url: str) -> Optional[bytes]:
    """下载图片原始数据"""
    try:
        resp = httpx.get(url, timeout=20, proxies={"http://": None, "https://": None})
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"[avatar] Download failed {url}: {e}")
    return None


def _process_to_2_3(img_data: bytes) -> Optional[bytes]:
    """
    将图片处理为 2:3 比例（居中裁剪）
    参考 gfriends-inputer fix_size type=2
    """
    try:
        img = Image.open(io.BytesIO(img_data))
        img = ImageOps.exif_transpose(img)  # 纠正方向
        wf, hf = img.size
        target_ratio = 2 / 3

        # 如果比例接近，直接返回
        if abs(wf / hf - target_ratio) < 0.02:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue()

        # 居中裁剪为 2:3
        if wf / hf > target_ratio:
            # 太宽：左右裁
            new_w = int(hf * target_ratio)
            left = (wf - new_w) // 2
            img = img.crop((left, 0, left + new_w, hf))
        else:
            # 太窄：上下裁
            new_h = int(wf / target_ratio)
            top = (hf - new_h) // 2
            img = img.crop((0, top, wf, top + new_h))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        print(f"[avatar] Process image error: {e}")
        return None


def _name_to_cache_key(name: str) -> str:
    """演员名转缓存文件名"""
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:12]


def get_avatar(name: str, force_download: bool = False) -> Optional[str]:
    """
    获取演员头像本地路径
    1. 检查本地缓存
    2. 从 gfriends 下载并处理
    3. 返回本地文件路径（相对URL）
    """
    cache_key = _name_to_cache_key(name)
    local_path = AVATAR_CACHE_DIR / f"{cache_key}.jpg"

    # 有缓存直接返回
    if not force_download and local_path.exists():
        return f"/api/actors/avatar/{name}"

    # 下载并处理
    filetree = _get_filetree()
    if not filetree:
        return None

    avatar_info = _find_best_avatar(name, filetree)
    if not avatar_info:
        return None

    company, filename = avatar_info
    url = f"{GFRIENDS_REPO}/Content/{quote(company, safe='')}/{quote(filename, safe='')}"
    raw_data = _download_raw(url)
    if not raw_data:
        return None

    processed = _process_to_2_3(raw_data)
    if not processed:
        return None

    # 保存
    with open(local_path, "wb") as f:
        f.write(processed)

    return f"/api/actors/avatar/{name}"


def get_avatar_data(name: str):
    """返回头像的本地文件路径，供 FastAPI 直接读取"""
    cache_key = _name_to_cache_key(name)
    local_path = AVATAR_CACHE_DIR / f"{cache_key}.jpg"
    if local_path.exists():
        return local_path
    return None
