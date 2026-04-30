import httpx
import logging
from typing import Optional, List
from config import config

logger = logging.getLogger(__name__)

class OpenListClient:
    def __init__(self):
        self.api_url = config.openlist_api_url.rstrip('/')
        self.token = config.openlist_token
        self.username = config.openlist_username
        self.password = config.openlist_password
        self.default_path = config.openlist_default_path

    def _get_headers(self):
        return {
            "Authorization": self.token,
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
        }

    async def _refresh_token(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.api_url}/api/auth/login",
                    json={"username": self.username, "password": self.password},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 200:
                        self.token = data.get('data', {}).get('token', '')
                        if self.token:
                            config._config.setdefault('openlist', {})['token'] = self.token
                            from pathlib import Path
                            config_path = Path(__file__).parent.parent.parent / "config.yaml"
                            import yaml
                            with open(config_path, 'r', encoding='utf-8') as f:
                                yaml_data = yaml.safe_load(f)
                            yaml_data['openlist']['token'] = self.token
                            with open(config_path, 'w', encoding='utf-8') as f:
                                yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)
                            logger.info("OpenList token refreshed successfully")
                            return True
            return False
        except Exception as e:
            logger.error(f"OpenList token refresh failed: {e}")
            return False

    def _normalize_path(self, path: str) -> str:
        if path.startswith('/dav/'):
            path = path[4:]
        if not path.startswith('/'):
            path = '/' + path
        return path

    async def add_offline_download(self, path: str, urls: List[str], tool: str = "115 Open") -> Optional[str]:
        if not self.token and not await self._refresh_token():
            logger.error("No token configured and refresh failed")
            return None

        normalized_path = self._normalize_path(path)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.api_url}/api/fs/add_offline_download",
                    json={
                        "path": normalized_path,
                        "urls": urls,
                        "tool": tool,
                        "delete_policy": "upload_download_stream"
                    },
                    headers=self._get_headers(),
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 401:
                        logger.info("OpenList token expired, refreshing...")
                        if await self._refresh_token():
                            return await self.add_offline_download(path, urls, tool)
                        return None
                    if data.get('code') == 200:
                        return data.get('message', 'success')
                    else:
                        logger.error(f"OpenList error: {data}")
                        return None
                else:
                    logger.error(f"OpenList HTTP error: {resp.status_code}")
                    return None

        except Exception as e:
            logger.error(f"OpenList request failed: {e}")
            return None

    async def mkdir(self, path: str) -> bool:
        if not self.token and not await self._refresh_token():
            return False

        normalized = self._normalize_path(path)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.api_url}/api/fs/mkdir",
                    json={"path": normalized},
                    headers=self._get_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('code') == 200
        except Exception as e:
            logger.error(f"Mkdir failed: {e}")
        return False

    async def get_offline_tasks(self) -> List[dict]:
        if not self.token and not await self._refresh_token():
            return []

        all_tasks = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp_undone = await client.get(
                    f"{self.api_url}/api/task/offline_download/undone",
                    headers=self._get_headers(),
                )
                if resp_undone.status_code == 200:
                    data = resp_undone.json()
                    if data.get('code') == 200:
                        all_tasks.extend(data.get('data', []))

                resp_done = await client.get(
                    f"{self.api_url}/api/task/offline_download/done",
                    headers=self._get_headers(),
                )
                if resp_done.status_code == 200:
                    data = resp_done.json()
                    if data.get('code') == 200:
                        all_tasks.extend(data.get('data', []))

        except Exception as e:
            logger.error(f"Get offline tasks failed: {e}")

        return all_tasks

openlist_client = OpenListClient()
