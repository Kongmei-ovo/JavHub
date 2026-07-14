#!/usr/bin/env node

import { pathToFileURL } from "node:url";

const DEFAULT_BASE_URL =
  process.env.API_LOAD_BASE_URL || process.env.JAVHUB_BASE_URL || "http://localhost:3000";

const DEFAULT_ENDPOINTS = [
  "/health",
  "/api/v1/cache/stats",
  "/api/v1/videos?page=1&page_size=20&include_total=false",
  "/api/v1/videos/search?page=1&page_size=20&include_total=false",
  "/api/v1/actresses?page=1&page_size=20",
  "/api/v1/actors?page=1&page_size=20",
  "/api/v1/directors?page=1&page_size=20",
  "/api/v1/authors?page=1&page_size=20",
  "/api/v1/categories",
  "/api/v1/makers?page=1&page_size=20",
  "/api/v1/labels?page=1&page_size=20",
  "/api/v1/series?page=1&page_size=20",
  "/health/readiness",
];

const OPERATIONS_ENDPOINTS = [
  "/health/readiness",
  "/api/v1/downloads/candidates/summary",
  "/api/v1/scheduler/jobs",
  "/api/v1/cache/stats",
  "/api/v1/logs/summary?since_minutes=1440",
];

const ENDPOINT_GROUPS = Object.freeze({
  default: DEFAULT_ENDPOINTS,
  operations: OPERATIONS_ENDPOINTS,
});

const SCENARIOS = new Set(["default", "cold", "warm", "hot"]);

const DEFAULT_STAGES = [
  { name: "warm", concurrency: 10, durationMs: 30_000 },
  { name: "hot", concurrency: 24, durationMs: 60_000 },
  { name: "stress", concurrency: 64, durationMs: 60_000 },
];

const FAILURE_LIMIT = 50;
const SLOWEST_LIMIT = 10;

function printHelp() {
  console.log(`Usage:
  node scripts/api_load_test.mjs [options]

Options:
  --base <url>                 Base URL to test. Defaults to API_LOAD_BASE_URL,
                               JAVHUB_BASE_URL, then ${DEFAULT_BASE_URL}
  --stages <spec>              Comma-separated stage spec: name:concurrency:duration.
                               Example: warm:10:30s,hot:24:60s,stress:64:60s
  --warm-duration <duration>   Override warm duration. Examples: 30s, 1m, 500ms
  --hot-duration <duration>    Override hot duration.
  --stress-duration <duration> Override stress duration.
  --duration-scale <number>    Multiply all stage durations. Useful for smoke runs.
  --timeout <duration>         Per-request timeout. Default: 15s
  --purge                      POST /api/v1/cache/purge?scope=all before testing.
                               This is off by default.
  --scenario <default|cold|warm|hot>
                               Cache scenario. default keeps existing behavior;
                               cold purges first; warm runs a preflight warmup pass;
                               hot keeps the existing cache.
  --endpoint-group <default|operations>
                               Use a built-in read-only endpoint group.
                               Default: default.
  --endpoint <path-or-url>     Add one endpoint. May be repeated. When provided,
                               replaces the selected read-only endpoint group.
  --help                       Show this help.

Output:
  Writes a JSON summary to stdout. Failures count only network errors and
  unexpected non-2xx responses from the tested read-only endpoint list.
`);
}

function parseDuration(value, flagName) {
  const match = String(value).trim().match(/^(\d+(?:\.\d+)?)(ms|s|m)?$/);
  if (!match) {
    throw new Error(`Invalid duration for ${flagName}: ${value}`);
  }
  const amount = Number(match[1]);
  const unit = match[2] || "s";
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error(`Invalid duration for ${flagName}: ${value}`);
  }
  if (unit === "ms") return Math.round(amount);
  if (unit === "s") return Math.round(amount * 1000);
  if (unit === "m") return Math.round(amount * 60_000);
  throw new Error(`Invalid duration unit for ${flagName}: ${value}`);
}

function parseStages(value) {
  return String(value)
    .split(",")
    .map((raw) => raw.trim())
    .filter(Boolean)
    .map((raw) => {
      const parts = raw.split(":");
      if (parts.length !== 3) {
        throw new Error(`Invalid stage "${raw}". Expected name:concurrency:duration.`);
      }
      const concurrency = Number(parts[1]);
      if (!Number.isInteger(concurrency) || concurrency < 1) {
        throw new Error(`Invalid concurrency in stage "${raw}".`);
      }
      return {
        name: parts[0],
        concurrency,
        durationMs: parseDuration(parts[2], `--stages ${parts[0]}`),
      };
    });
}

function parseArgs(argv) {
  const config = {
    baseUrl: DEFAULT_BASE_URL,
    endpoints: [],
    stages: DEFAULT_STAGES.map((stage) => ({ ...stage })),
    timeoutMs: 15_000,
    purge: false,
    scenario: "default",
    warmup: false,
    endpointGroup: "default",
    help: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = () => {
      i += 1;
      if (i >= argv.length) throw new Error(`Missing value for ${arg}`);
      return argv[i];
    };

    if (arg === "--help" || arg === "-h") {
      config.help = true;
    } else if (arg === "--base") {
      config.baseUrl = next();
    } else if (arg === "--stages") {
      config.stages = parseStages(next());
    } else if (arg === "--warm-duration") {
      config.stages.find((stage) => stage.name === "warm").durationMs = parseDuration(next(), arg);
    } else if (arg === "--hot-duration") {
      config.stages.find((stage) => stage.name === "hot").durationMs = parseDuration(next(), arg);
    } else if (arg === "--stress-duration") {
      config.stages.find((stage) => stage.name === "stress").durationMs = parseDuration(next(), arg);
    } else if (arg === "--duration-scale") {
      const scale = Number(next());
      if (!Number.isFinite(scale) || scale <= 0) {
        throw new Error(`Invalid --duration-scale value: ${scale}`);
      }
      config.stages = config.stages.map((stage) => ({
        ...stage,
        durationMs: Math.max(1, Math.round(stage.durationMs * scale)),
      }));
    } else if (arg === "--timeout") {
      config.timeoutMs = parseDuration(next(), arg);
    } else if (arg === "--purge") {
      config.purge = true;
    } else if (arg === "--scenario") {
      config.scenario = next();
      if (!SCENARIOS.has(config.scenario)) {
        throw new Error(`Invalid --scenario value: ${config.scenario}`);
      }
    } else if (arg === "--endpoint-group") {
      config.endpointGroup = next();
      if (!Object.hasOwn(ENDPOINT_GROUPS, config.endpointGroup)) {
        throw new Error(`Invalid --endpoint-group value: ${config.endpointGroup}`);
      }
    } else if (arg === "--endpoint") {
      config.endpoints.push(next());
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }

  if (!config.help) {
    config.baseUrl = normalizeBaseUrl(config.baseUrl);
    if (config.endpoints.length === 0) {
      config.endpoints = [...ENDPOINT_GROUPS[config.endpointGroup]];
    }
    applyScenario(config);
  }
  return config;
}

function applyScenario(config) {
  if (config.scenario === "cold") {
    config.purge = true;
  } else if (config.scenario === "warm") {
    config.warmup = true;
  } else if (config.scenario === "hot") {
    config.purge = false;
    config.warmup = false;
  }
}

function normalizeBaseUrl(baseUrl) {
  const normalized = String(baseUrl || "").trim().replace(/\/+$/, "");
  if (!normalized) throw new Error("Base URL is required.");
  new URL(normalized);
  return normalized;
}

function buildUrl(baseUrl, pathOrUrl) {
  if (/^https?:\/\//i.test(pathOrUrl)) {
    return pathOrUrl;
  }
  const path = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${baseUrl}${path}`;
}

function createStats() {
  return {
    requests: 0,
    statuses: {},
    failures: 0,
    server_errors: 0,
    latencies: [],
    failure_samples: [],
    endpointStats: new Map(),
  };
}

function recordEndpoint(stats, endpoint, latencyMs, failed) {
  if (!stats.endpointStats.has(endpoint)) {
    stats.endpointStats.set(endpoint, {
      endpoint,
      requests: 0,
      failures: 0,
      latencies: [],
    });
  }
  const endpointStats = stats.endpointStats.get(endpoint);
  endpointStats.requests += 1;
  endpointStats.failures += failed ? 1 : 0;
  endpointStats.latencies.push(latencyMs);
}

function recordResult(stats, result) {
  stats.requests += 1;
  stats.latencies.push(result.latencyMs);
  stats.statuses[result.status] = (stats.statuses[result.status] || 0) + 1;
  const failed = result.error || result.status < 200 || result.status >= 300;
  if (failed) {
    stats.failures += 1;
    if (stats.failure_samples.length < FAILURE_LIMIT) {
      stats.failure_samples.push({
        endpoint: result.endpoint,
        status: result.status,
        error: result.error,
        latency_ms: result.latencyMs,
      });
    }
  }
  if (result.status >= 500) {
    stats.server_errors += 1;
  }
  recordEndpoint(stats, result.endpoint, result.latencyMs, failed);
}

function mergeStats(target, source) {
  target.requests += source.requests;
  target.failures += source.failures;
  target.server_errors += source.server_errors;
  target.latencies.push(...source.latencies);
  target.failure_samples.push(...source.failure_samples.slice(0, FAILURE_LIMIT - target.failure_samples.length));
  for (const [status, count] of Object.entries(source.statuses)) {
    target.statuses[status] = (target.statuses[status] || 0) + count;
  }
  for (const sourceEndpoint of source.endpointStats.values()) {
    if (!target.endpointStats.has(sourceEndpoint.endpoint)) {
      target.endpointStats.set(sourceEndpoint.endpoint, {
        endpoint: sourceEndpoint.endpoint,
        requests: 0,
        failures: 0,
        latencies: [],
      });
    }
    const targetEndpoint = target.endpointStats.get(sourceEndpoint.endpoint);
    targetEndpoint.requests += sourceEndpoint.requests;
    targetEndpoint.failures += sourceEndpoint.failures;
    targetEndpoint.latencies.push(...sourceEndpoint.latencies);
  }
}

async function timedFetch(url, endpoint, timeoutMs) {
  const started = performance.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    await response.arrayBuffer();
    return {
      endpoint,
      status: response.status,
      latencyMs: Math.round(performance.now() - started),
      error: null,
    };
  } catch (error) {
    return {
      endpoint,
      status: "ERR",
      latencyMs: Math.round(performance.now() - started),
      error: error && error.name === "AbortError" ? "timeout" : String(error?.message || error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchJson(baseUrl, path, timeoutMs) {
  const url = buildUrl(baseUrl, path);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
    const text = await response.text();
    if (!response.ok) {
      return { ok: false, status: response.status, error: text.slice(0, 200) };
    }
    return { ok: true, status: response.status, data: text ? JSON.parse(text) : null };
  } catch (error) {
    return { ok: false, status: "ERR", error: String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

async function purgeCache(baseUrl, timeoutMs) {
  const url = buildUrl(baseUrl, "/api/v1/cache/purge?scope=all");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { method: "POST", signal: controller.signal });
    const text = await response.text();
    return {
      ok: response.ok,
      status: response.status,
      body: text ? JSON.parse(text) : null,
    };
  } catch (error) {
    return { ok: false, status: "ERR", error: String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

async function runStage(stage, config) {
  const stats = createStats();
  const started = performance.now();
  const endsAt = started + stage.durationMs;
  let cursor = 0;

  async function worker() {
    while (performance.now() < endsAt) {
      const endpoint = config.endpoints[cursor % config.endpoints.length];
      cursor += 1;
      const result = await timedFetch(buildUrl(config.baseUrl, endpoint), endpoint, config.timeoutMs);
      recordResult(stats, result);
    }
  }

  const workers = Array.from({ length: stage.concurrency }, () => worker());
  await Promise.all(workers);

  return {
    name: stage.name,
    concurrency: stage.concurrency,
    duration_ms: Math.round(performance.now() - started),
    stats,
  };
}

async function runWarmup(config) {
  const stats = createStats();
  const started = performance.now();
  for (const endpoint of config.endpoints) {
    const result = await timedFetch(buildUrl(config.baseUrl, endpoint), endpoint, config.timeoutMs);
    recordResult(stats, result);
  }
  return {
    duration_ms: Math.round(performance.now() - started),
    stats,
  };
}

function percentile(sortedValues, p) {
  if (sortedValues.length === 0) return 0;
  const index = Math.ceil((p / 100) * sortedValues.length) - 1;
  return sortedValues[Math.max(0, Math.min(sortedValues.length - 1, index))];
}

function summarizeLatencies(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const total = sorted.reduce((sum, value) => sum + value, 0);
  return {
    avg: sorted.length ? Number((total / sorted.length).toFixed(2)) : 0,
    p50: percentile(sorted, 50),
    p90: percentile(sorted, 90),
    p95: percentile(sorted, 95),
    p99: percentile(sorted, 99),
    max: sorted.length ? sorted[sorted.length - 1] : 0,
  };
}

function summarizeEndpoint(endpointStats) {
  const latency = summarizeLatencies(endpointStats.latencies);
  return {
    endpoint: endpointStats.endpoint,
    requests: endpointStats.requests,
    failures: endpointStats.failures,
    avg: latency.avg,
    p95: latency.p95,
    p99: latency.p99,
    max: latency.max,
  };
}

function summarizeStats(stats, durationMs) {
  const latency = summarizeLatencies(stats.latencies);
  const slowest = [...stats.endpointStats.values()]
    .map(summarizeEndpoint)
    .sort((a, b) => b.p95 - a.p95 || b.max - a.max)
    .slice(0, SLOWEST_LIMIT);

  return {
    requests: stats.requests,
    rps: durationMs > 0 ? Number((stats.requests / (durationMs / 1000)).toFixed(2)) : 0,
    statuses: stats.statuses,
    failures: stats.failures,
    server_errors: stats.server_errors,
    ...latency,
    slowest_by_endpoint: slowest,
    failure_samples: stats.failure_samples,
  };
}

async function main() {
  const config = parseArgs(process.argv.slice(2));
  if (config.help) {
    printHelp();
    return;
  }

  const runStarted = new Date();
  const cacheBefore = await fetchJson(config.baseUrl, "/api/v1/cache/stats", config.timeoutMs);
  const purge = config.purge ? await purgeCache(config.baseUrl, config.timeoutMs) : null;
  const warmup = config.warmup ? await runWarmup(config) : null;

  const aggregate = createStats();
  const stageSummaries = [];
  let measuredDurationMs = 0;
  for (const stage of config.stages) {
    const result = await runStage(stage, config);
    measuredDurationMs += result.duration_ms;
    mergeStats(aggregate, result.stats);
    stageSummaries.push({
      name: result.name,
      concurrency: result.concurrency,
      duration_ms: result.duration_ms,
      ...summarizeStats(result.stats, result.duration_ms),
    });
  }

  const cacheAfter = await fetchJson(config.baseUrl, "/api/v1/cache/stats", config.timeoutMs);
  const summary = {
    base_url: config.baseUrl,
    started_at: runStarted.toISOString(),
    finished_at: new Date().toISOString(),
    scenario: config.scenario,
    endpoint_group: config.endpointGroup,
    stages: config.stages.map((stage) => ({
      name: stage.name,
      concurrency: stage.concurrency,
      duration_ms: stage.durationMs,
    })),
    endpoints: config.endpoints,
    purge,
    warmup: warmup
      ? {
          duration_ms: warmup.duration_ms,
          ...summarizeStats(warmup.stats, warmup.duration_ms),
        }
      : null,
    cache_before: cacheBefore.ok ? cacheBefore.data : cacheBefore,
    cache_after: cacheAfter.ok ? cacheAfter.data : cacheAfter,
    stage_summaries: stageSummaries,
    ...summarizeStats(aggregate, measuredDurationMs),
  };

  console.log(JSON.stringify(summary, null, 2));
  if (summary.failures > 0 || summary.server_errors > 0) {
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error?.stack || error);
    process.exitCode = 1;
  });
}

export { ENDPOINT_GROUPS, parseArgs };
