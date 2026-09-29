"""Reproducible token-savings benchmark for jtoken.

Counts tiktoken (cl100k_base) tokens for pretty-printed JSON versus the
jtoken representation across representative payload shapes, and verifies
that every payload round-trips losslessly (encode_document -> decode_document).

Format-specific wrappers (Mongo extended-JSON $oid/$date, ES hit envelopes)
are restored via the output target that matches each document's dialect.
Documents are encoded one by one, as they would be injected into a prompt.

Run from the repo root:

    python3 benchmarks/benchmark.py

A JSON table is printed to stdout for pasting into the README.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import tiktoken

import jtoken

ENCODING = tiktoken.get_encoding("cl100k_base")

N_DOCS = 50
REPEAT_ROUNDS = 3


def count(text: str) -> int:
    return len(ENCODING.encode(text))


def make_elasticsearch_hits(n: int) -> list[dict[str, Any]]:
    """E-commerce search-index documents, one ES _search hit per item."""
    categories = ["electronics", "apparel", "home", "outdoors", "books"]
    brands = ["Acme", "Globex", "Initech", "Umbrella", "Stark Industries"]
    titles = [
        "Wireless Noise-Cancelling Headphones",
        "Merino Wool Base Layer",
        "Cast Iron Skillet 12-inch",
        "Insulated Trail Water Bottle",
        "Mechanical Keyboard 75%",
    ]
    hits = []
    for i in range(n):
        hits.append(
            {
                "_index": "products",
                "_id": f"prod_{i:06d}",
                "_score": round(1.0 - i / (n * 10), 4),
                "_source": {
                    "title": titles[i % len(titles)],
                    "brand": brands[i % len(brands)],
                    "category": {"id": i % 5 + 1, "name": categories[i % 5]},
                    "price": {"amount": round(19.99 + (i % 17) * 8.5, 2), "currency": "EUR"},
                    "rating": {"average": round(3.1 + (i % 19) / 10, 2), "count": 40 + i * 7},
                    "tags": [categories[(i + j) % 5] for j in range(3)],
                    "in_stock": i % 3 != 0,
                    "free_shipping": i % 4 == 0,
                    "description": (
                        f"The {titles[i % len(titles)].lower()} from {brands[i % len(brands)]}. "
                        "Built for daily use with durable materials, one-year warranty and "
                        "free returns within 30 days. Popular with customers worldwide."
                    ),
                    "attributes": {"color": ["black", "silver", "navy"][i % 3], "weight_g": 120 + i},
                    "created_at": f"2026-08-{i % 28 + 1:02d}T10:00:00Z",
                },
            }
        )
    return hits


def make_mongo_documents(n: int) -> list[dict[str, Any]]:
    """User-activity MongoDB documents with ObjectId/$date extended JSON."""
    actions = ["page_view", "add_to_cart", "purchase", "search", "logout"]
    pages = ["/home", "/pricing", "/blog/llm-tokens", "/checkout", "/docs/api"]
    docs = []
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for i in range(n):
        docs.append(
            {
                "_id": {"$oid": f"{i:024x}"},
                "user_id": f"user_{10000 + i}",
                "session_id": f"sess_{i:08d}",
                "action": actions[i % len(actions)],
                "page": {"path": pages[i % len(pages)], "referrer": "https://www.google.com/"},
                "device": {"type": ["desktop", "mobile", "tablet"][i % 3], "os": ["macOS", "iOS", "Windows"][i % 3]},
                "geo": {"country": ["DE", "EE", "US"][i % 3], "city": ["Berlin", "Tallinn", "New York"][i % 3]},
                "duration_ms": 1200 + i * 37,
                "converted": i % 5 == 0,
                "bot": False,
                "timestamp": {"$date": {"$numberLong": str(int((base + timedelta(minutes=i * 3)).timestamp() * 1000))}},
                "tags": [actions[(i + j) % 5] for j in range(2)],
            }
        )
    return docs


def make_api_events(n: int) -> list[dict[str, Any]]:
    """Generic SaaS webhook / analytics events (deeply nested standard JSON)."""
    levels = ["info", "warning", "error"]
    sources = ["billing", "auth", "ingest", "scheduler"]
    events = []
    for i in range(n):
        events.append(
            {
                "event_id": f"evt_{i:08d}",
                "level": levels[i % 3],
                "source": sources[i % 4],
                "message": f"Processed batch {i} with 128 records in {50 + i % 90}ms",
                "created": f"2026-09-{i % 28 + 1:02d}T06:{i % 60:02d}:00Z",
                "actor": {"id": f"u_{2000 + i}", "name": ["alice", "bob", "carol"][i % 3], "roles": ["user", "admin" if i % 9 == 0 else "member"]},
                "payload": {
                    "batch": {"id": f"b_{i}", "records": 128, "failures": i % 7, "retries": 0 if i % 2 == 0 else 1},
                    "context": {"region": "eu-central-1", "trace_id": f"trc_{i:012x}", "retry": False},
                    "nested": {"a": {"b": {"c": {"depth": 4, "ok": True, "value": round(i * 1.5, 2)}}}},
                },
                "tags": [sources[(i + j) % 4] for j in range(2)],
            }
        )
    return events


def _target_for(context: jtoken.NormalizationContext) -> str:
    if context.elastic is not None:
        return "elastic_hit"
    if context.source_format in ("mongo_extended", "mongo_shell"):
        return "mongo_extended"
    return "json"


def encode_payload(items: list[dict[str, Any]]) -> tuple[str, list[tuple[Any, str, str]]]:
    """Encode each document individually (auto-detects its dialect), joined by
    newlines as they would appear in a prompt. Returns (text, per-item info)."""
    parts = []
    info = []
    for item in items:
        text, context = jtoken.encode_document(item)
        parts.append(text)
        info.append((item, text, _target_for(context)))
    return "\n".join(parts), info


def verify_lossless(data: Any, encoded: str, target: str) -> None:
    text, context = jtoken.encode_document(data)
    assert text == encoded, "encode() and encode_document() disagree"
    restored = jtoken.decode_document(text, target=target, context=context)
    expected = json.loads(json.dumps(data))
    assert restored == expected, f"round-trip mismatch (target={target!r})"


def run() -> None:
    datasets = [
        ("Elasticsearch hits (50 docs)", make_elasticsearch_hits(N_DOCS)),
        ("MongoDB documents (50 docs)", make_mongo_documents(N_DOCS)),
        ("Nested API events (50 events)", make_api_events(N_DOCS)),
    ]
    timings = []
    results = []
    for name, data in datasets:
        json_text = json.dumps(data, indent=2)
        t0 = time.perf_counter()
        for _ in range(REPEAT_ROUNDS):
            encoded, info = encode_payload(data)
        timings.append((time.perf_counter() - t0) / REPEAT_ROUNDS)
        for item, text, target in info:
            verify_lossless(item, text, target)
        results.append(
            {
                "payload": name,
                "json_tokens": count(json_text),
                "jtoken_tokens": count(encoded),
            }
        )

    print(f"{'Payload':<32} {'JSON':>10} {'jtoken':>10} {'Saved':>10} {'%':>7}")
    print("-" * 74)
    for r in results:
        saved = r["json_tokens"] - r["jtoken_tokens"]
        pct = saved / r["json_tokens"] * 100
        r["saved_pct"] = round(pct, 1)
        print(f"{r['payload']:<32} {r['json_tokens']:>10,} {r['jtoken_tokens']:>10,} {saved:>10,} {pct:>6.1f}%")
    print("-" * 74)
    total_json = sum(r["json_tokens"] for r in results)
    total_jt = sum(r["jtoken_tokens"] for r in results)
    print(f"{'TOTAL':<32} {total_json:>10,} {total_jt:>10,} {total_json - total_jt:>10,} {(total_json - total_jt) / total_json * 100:>6.1f}%")
    print("\nEncoder timing (per document, %d-round average): %s" % (REPEAT_ROUNDS, ", ".join(f"{t / N_DOCS * 1000:.2f} ms" for t in timings)))
    print("All payloads verified lossless: encode_document -> decode_document -> equal.")
    print("\nJSON for README:\n" + json.dumps(results, indent=2))


if __name__ == "__main__":
    run()