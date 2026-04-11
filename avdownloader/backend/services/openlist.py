import httpx
from typing import Optional, List
from config import config

class OpenListClient:
    def __init__(self):
        self.api_url = config.openlist_api_url.rstrip('/')
        self.token = config.openlist_token
        self.username = config.openlist_username
        self.password = config.openlist_password
        self.default_path = config.openlist_default_path

    def _get_headers(self):
        # OpenList fs API 不需要 "Bearer" 前缀，直接使用token
        return {
            "Authorization": self.token,
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
        }

    def _refresh_token(self) -> bool:
        """
        刷新 token，当 token 过期时自动调用
        """
        try:
            resp = httpx.post(
                f"{self.api_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=30,
                proxies={"http://": None, "https://": None}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 200:
                    self.token = data.get('data', {}).get('token', '')
                    if self.token:
                        # 更新 config 中的 token
                        config._config.setdefault('openlist', {})['token'] = self.token
                        # 持久化到文件
                        from pathlib import Path
                        config_path = Path(__file__).parent.parent.parent / "config.yaml"
                        import yaml
                        with open(config_path, 'r', encoding='utf-8') as f:
                            yaml_data = yaml.safe_load(f)
                        yaml_data['openlist']['token'] = self.token
                        with open(config_path, 'w', encoding='utf-8') as f:
                            yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)
                        print(f"OpenList token refreshed successfully")
                        return True
            return False
        except Exception as e:
            print(f"OpenList token refresh failed: {e}")
            return False

    def _normalize_path(self, path: str) -> str:
        """
        规范化路径，OpenList存储路径格式转换
        /dav/115/AV -> /115/AV
        /115/AV -> /115/AV
        """
        # 移除 /dav 前缀（如果存在）
        if path.startswith('/dav/'):
            path = path[4:]
        # 确保路径以 / 开头
        if not path.startswith('/'):
            path = '/' + path
        return path

    def add_offline_download(self, path: str, urls: List[str], tool: str = "115 Open") -> Optional[str]:
        """
        添加离线下载任务

        Args:
            path: 下载路径，如 /115/AV/演员名
            urls: 磁力链接数组
            tool: 下载工具，默认 115 Open（需要 OpenList 配置 115 云盘）
        """
        if not self.token and not self._refresh_token():
            print("No token configured and refresh failed")
            return None

        # 规范化路径
        normalized_path = self._normalize_path(path)

        try:
            resp = httpx.post(
                f"{self.api_url}/api/fs/add_offline_download",
                json={
                    "path": normalized_path,
                    "urls": urls,
                    "tool": tool,
                    "delete_policy": "upload_download_stream"
                },
                headers=self._get_headers(),
                timeout=30,
                proxies={"http://": None, "https://": None}
            )

            if resp.status_code == 200:
                data = resp.json()
                # token 过期，尝试刷新后重试
                if data.get('code') == 401:
                    print("OpenList token expired, refreshing...")
                    if self._refresh_token():
                        return self.add_offline_download(path, urls, tool)
                    return None
                if data.get('code') == 200:
                    return data.get('message', 'success')
                else:
                    print(f"OpenList error: {data}")
                    return None
            else:
                print(f"OpenList HTTP error: {resp.status_code}")
                return None

        except Exception as e:
            print(f"OpenList request failed: {e}")
            return None

    def mkdir(self, path: str) -> bool:
        """
        创建目录（如果不存在则自动创建父目录）
        """
        if not self.token and not self._refresh_token():
            return False

        normalized = self._normalize_path(path)

        try:
            resp = httpx.post(
                f"{self.api_url}/api/fs/mkdir",
                json={"path": normalized},
                headers=self._get_headers(),
                timeout=30,
                proxies={"http://": None, "https://": None}
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get('code') == 200
        except Exception as e:
            print(f"Mkdir failed: {e}")
        return False

    def get_offline_tasks(self) -> List[dict]:
        """
        获取所有离线下载任务（进行中 + 已完成）
        OpenList state: 0=pending, 1=running, 2=succeeded, 7=failed
        """
        if not self.token and not self._refresh_token():
            return []

        all_tasks = []
        try:
            # 获取进行中的任务
            resp_undone = httpx.get(
                f"{self.api_url}/api/task/offline_download/undone",
                headers=self._get_headers(),
                timeout=30,
                proxies={"http://": None, "https://": None}
            )
            if resp_undone.status_code == 200:
                data = resp_undone.json()
                if data.get('code') == 200:
                    all_tasks.extend(data.get('data', []))

            # 获取已完成/失败的任务
            resp_done = httpx.get(
                f"{self.api_url}/api/task/offline_download/done",
                headers=self._get_headers(),
                timeout=30,
                proxies={"http://": None, "https://": None}
            )
            if resp_done.status_code == 200:
                data = resp_done.json()
                if data.get('code') == 200:
                    all_tasks.extend(data.get('data', []))

        except Exception as e:
            print(f"Get offline tasks failed: {e}")

        return all_tasks

openlist_client = OpenListClient()
