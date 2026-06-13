# Emby Movie Compatibility

JavHub exposes an optional Emby-compatible movie server. The catalog is always
the unified JavInfo catalog: a movie card exists before any file is downloaded.
115 Open files and online HLS are playback resources bound to the stable
JavHub ItemId; they never create, scrape, split, or merge movies.

## Enable

```yaml
emby_compat:
  enabled: true
  username: "javhub"
  password: "change-me"
```

Restart the backend after changing the setting. Existing in-memory tokens from
the older compatibility layer require one login; signed tokens issued by the
current layer survive service restarts and are invalidated when the username or
password changes.

Connect clients to the backend origin, normally:

```text
http://server-address:18090
```

Both root routes and `/emby` routes are supported. The server presents one
movie library. TV, music, Live TV, and administration probes return valid empty
Emby structures.

## Catalog And State

- ItemIds are JavHub catalog IDs, including `supp:<id>` where applicable.
- DMM mono, digital, and rental rows remain one grouped movie card.
- Actors use stable `person:<actress_id>` IDs.
- Favorites, watched state, playback progress, and continue watching share the
  same JavHub state used by the web UI.
- A movie without a 115 file remains visible and may use an online HLS source or
  receive a later ItemId-bound offline download.

## Playback

Each ready 115 video file is an Emby MediaSource. The default resource is first;
online HLS is last. Clients receive only stable JavHub URLs.

For original playback, JavHub resolves the 115 download URL when the final
player request arrives and forwards that exact request User-Agent to 115. HLS
playback uses the same-origin JavHub proxy. Temporary 115 download and
transcoding URLs are not stored or returned by catalog APIs.

## Reverse Proxy

When the backend is behind a path-aware reverse proxy, forward `/emby` and the
root Emby families to the backend:

```text
/emby
/System
/Users
/UserViews
/Library
/Items
/Persons
/Videos
/Sessions
/Shows
/Movies
/Genres
/Artists
/LiveTv
/Branding
/Localization
/DisplayPreferences
/CustomCssJS
/Web
/ScheduledTasks
/MediaSegments
/embywebsocket
```

Preserve `Host`, `X-Forwarded-Host`, and `X-Forwarded-Proto` so discovery
responses advertise the correct address. Do not strip the final player
`User-Agent`.
