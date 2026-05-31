# Cloudflare Access and Tunnel Deployment

This guide puts a login gate in front of JavHub for public web testing without
adding application-level users to JavHub yet.

```text
Browser
  -> Cloudflare Access
  -> Cloudflare Tunnel
  -> cloudflared container
  -> http://javhub:80
  -> JavHub Nginx and FastAPI
```

Use this when JavHub is deployed to a public server and you want only approved
test users to open the site. Cloudflare Access handles the login decision.
Cloudflare Tunnel carries traffic to the private Docker network, so the origin
server does not need to expose the JavHub port to the public internet.

## Cloudflare Setup

1. Add the domain you want to use, for example `javhub.example.com`, to
   Cloudflare.
2. Open Cloudflare Zero Trust.
3. Create a Cloudflare Tunnel using the `cloudflared` connector.
4. Copy the Docker token shown by Cloudflare. It becomes
   `CLOUDFLARE_TUNNEL_TOKEN` on the server.
5. Add a public hostname to the tunnel:
   - Subdomain: `javhub`
   - Domain: `example.com`
   - Service type: `HTTP`
   - Service URL: `http://javhub:80`
6. Create a Cloudflare Access self-hosted application for the same hostname.
7. Add an allow policy and only allow your email, or the small test group you
   trust. For first testing, 只放行你的邮箱.

The service URL is `http://javhub:80` because `cloudflared` runs in the same
Docker Compose network as the `javhub` service.

## Server Setup

Create or update `.env` next to `docker-compose.yml`:

```bash
JAVHUB_PORT=127.0.0.1:3000
JAVINFOAPI_PORT=127.0.0.1:18080
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...redacted...
```

`JAVHUB_PORT=127.0.0.1:3000` keeps the compose example useful for local health
checks while preventing the JavHub HTTP port from binding to the public network
interface. `JAVINFOAPI_PORT=127.0.0.1:18080` does the same for the companion
API. Do not commit `.env`; it contains the tunnel token.

Start JavHub with the Cloudflare override:

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml pull
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d
```

Check the local origin:

```bash
curl -fsS http://127.0.0.1:3000/health
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml logs -f cloudflared
```

Then open the public hostname in a browser. Cloudflare Access should show a
login step before JavHub loads.

## Public Exposure Checklist

- Do not put `CLOUDFLARE_TUNNEL_TOKEN` in GitHub, README snippets with real
  values, screenshots, or issue comments.
- 不要把 JavHub 端口直接暴露到公网. Do not expose Docker port `3000` or `80`
  to the public internet for this deployment. Keep JavHub reachable from the
  origin only through Cloudflare Tunnel.
- 不要把 JavInfoApi 端口直接暴露到公网. Bind `JAVINFOAPI_PORT` to `127.0.0.1`
  or remove the host port mapping if you do not need local host access.
- In the server firewall or cloud security group, remove inbound HTTP access to
  JavHub. Cloudflare Tunnel only needs outbound connectivity.
- Keep the Cloudflare Access policy narrow during testing. Start with only your
  own email, then add testers one at a time.
- Keep `/health` behind the same hostname unless you intentionally create a
  separate monitoring route.

## Updating

Run the same compose command when updating JavHub:

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml pull
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d
```

If the tunnel token is rotated in Cloudflare, update `CLOUDFLARE_TUNNEL_TOKEN`
in `.env` and restart only the tunnel:

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d cloudflared
```

## Troubleshooting

- Public hostname shows a Cloudflare error: check `cloudflared` logs and verify
  the tunnel public hostname points to `http://javhub:80`.
- JavHub opens without login: check that a Cloudflare Access application exists
  for the exact hostname and that the policy is active.
- Local `curl` works but the browser does not: check the Access policy, DNS
  record, and tunnel status in Zero Trust.
- Browser login works but API calls fail: confirm the public hostname routes all
  paths to the same tunnel and that the JavHub container is healthy.
