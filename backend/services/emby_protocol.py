"""Static Emby protocol payloads independent from the JavHub catalog."""
from __future__ import annotations

from typing import Any

from services.emby_mapper import SERVER_ID

EMBY_COMPAT_VERSION = "4.8.10.0"


def request_base_url(request: Any) -> str:
    headers = getattr(request, "headers", {}) or {}
    proto = str(headers.get("X-Forwarded-Proto") or headers.get("x-forwarded-proto") or "").split(",", 1)[0].strip()
    if not proto:
        url = getattr(request, "url", None)
        proto = str(getattr(url, "scheme", "") or "http")
    host = str(headers.get("X-Forwarded-Host") or headers.get("x-forwarded-host") or "").split(",", 1)[0].strip()
    if not host:
        host = str(headers.get("host") or "")
    return f"{proto}://{host}".rstrip("/") if host else ""


def system_info(request: Any, *, full: bool = False) -> dict:
    address = request_base_url(request)
    payload = {
        "Id": SERVER_ID,
        "ServerId": SERVER_ID,
        "ServerName": "JavHub",
        "Version": EMBY_COMPAT_VERSION,
        "ServerVersion": EMBY_COMPAT_VERSION,
        "ProductName": "Emby Server",
        "OperatingSystem": "Linux",
        "LocalAddress": address,
        "WanAddress": address,
        "PublishedServerUrl": address,
        "HttpServerPortNumber": 18090,
        "HttpsPortNumber": 0,
        "SupportsHttps": False,
        "SupportsAutoDiscovery": True,
        "StartupWizardCompleted": True,
    }
    if full:
        payload.update(
            {
                "Architecture": "X64",
                "HasPendingRestart": False,
                "IsShuttingDown": False,
                "SupportsLibraryMonitor": False,
                "WebSocketPortNumber": 18090,
                "CompletedInstallations": [],
                "CanSelfRestart": False,
                "CanLaunchWebBrowser": False,
                "CanRestart": False,
            }
        )
    return payload


def public_server_configuration() -> dict:
    return {
        "IsStartupWizardCompleted": True,
        "EnableRemoteAccess": True,
        "EnableUPnP": False,
        "EnableHttps": False,
        "RequireHttps": False,
        "LocalNetworkSubnets": [],
        "LocalNetworkAddresses": [],
        "RemoteClientBitrateLimit": 0,
    }


def startup_configuration() -> dict:
    return {
        "IsStartupWizardCompleted": True,
        "StartupWizardCompleted": True,
        "EnableRemoteAccess": True,
        "UICulture": "zh-CN",
        "MetadataCountryCode": "CN",
        "PreferredMetadataLanguage": "zh-CN",
    }


def server_configuration() -> dict:
    return {
        "EnableFolderView": True,
        "EnableGroupingIntoCollections": True,
        "EnableExternalContentInSuggestions": False,
        "ImageSavingConvention": "Compatible",
    }


def display_preferences(pref_id: str) -> dict:
    return {
        "Id": pref_id,
        "SortBy": "SortName",
        "SortOrder": "Ascending",
        "CustomPrefs": {
            "homesection0": "smalllibrarytiles",
            "homesection1": "resume",
            "homesection2": "latestmedia",
        },
    }


def localization_cultures() -> list[dict]:
    return [
        {
            "DisplayName": "简体中文",
            "Name": "zh-CN",
            "ThreeLetterISOLanguageName": "zho",
            "TwoLetterISOLanguageName": "zh",
            "ThreeLetterISOLanguageNames": ["zho", "chi"],
            "IsRightToLeft": False,
        },
        {
            "DisplayName": "English",
            "Name": "en-US",
            "ThreeLetterISOLanguageName": "eng",
            "TwoLetterISOLanguageName": "en",
            "ThreeLetterISOLanguageNames": ["eng"],
            "IsRightToLeft": False,
        },
    ]
