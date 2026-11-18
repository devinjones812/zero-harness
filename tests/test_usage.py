import pytest

from zero_harness.models.reply import Usage
from zero_harness.usage import dollars

RATES = {
    "input": 2,
    "output": 10,
    "cache_read": 0.1,
    "cache_write": 2.5,
    "tiers": [{"input": 4, "output": 15, "cache_read": 0.2, "cache_write": 5, "tier": {"type": "context", "size": 272_000}}],
}


def test_splits_input_into_uncached_read_and_written():
    usage = Usage(input_tokens=100_000, cached_tokens=50_000, output_tokens=10_000, cache_write_tokens=20_000)
    # 30k uncached at $2, 50k read at $0.1, 20k written at $2.5, 10k output at $10
    assert dollars(usage, RATES) == pytest.approx(0.06 + 0.005 + 0.05 + 0.1)


def test_long_context_tier():
    usage = Usage(input_tokens=300_000, cached_tokens=0, output_tokens=0)
    assert dollars(usage, RATES) == pytest.approx(1.2)


def test_missing_cache_rates_fall_back_to_input():
    usage = Usage(input_tokens=100, cached_tokens=40, output_tokens=0, cache_write_tokens=60)
    assert dollars(usage, {"input": 1_000_000, "output": 0}) == pytest.approx(100)
