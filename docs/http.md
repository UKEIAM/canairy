# HTTP behaviour

All clients send their requests through the same transport stack, built by
`canairy._http.build_client`:

```text
httpx2.Client → CacheTransport → RetryTransport → RateLimitTransport → HTTPTransport
```

The limiter sits below the cache, so cache hits don't count against the budget, and below the
retry layer, so every retry does.

## Caching

Responses are cached with [hishel](https://hishel.com) in `.cache/hishel/hishel_cache_v2.db`
under the current working directory, for as long as the servers allow (RFC 9111):

| Source | Cached for |
|---|---|
| UBA | 3 hours, measurements included |
| HH, BE | 5 minutes |
| NI | a few minutes (no `Cache-Control`; heuristic freshness from `Last-Modified`) |
| NRW | not cached (`Cache-Control: max-age=0`) |

Repeated calls within that time don't hit the API. Other files in `.cache/hishel/`, left by
canairy versions before the switch to hishel 2.0, are no longer read and can be deleted.

`canairy` keeps hishel's `rfc=True`: hishel 2.0's default ignores `Cache-Control` and caches
every GET forever.

## Rate limiting

At most 120 requests per 60 seconds (sliding window) **per API host, process-wide**. Each data
source has its own budget, and extra client instances don't raise it. When the limit is
reached, the next request waits.

## Retries

- Dropped connections (`RemoteProtocolError`, also while reading the body) are retried for all
  clients.
- The UBA client also retries HTTP 429 and 5xx; other 4xx raise `HTTPStatusError` at once.
- Up to 8 attempts with exponential backoff (`2**i` seconds). Once they are exhausted, the last
  error is raised or the last response returned.
- Timeouts (60 s) and connect errors are not retried.

## Proxies

Because the clients pass an explicit transport, proxies from `HTTP_PROXY`/`HTTPS_PROXY` are
not used.
