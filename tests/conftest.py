"""Test-suite global setup.

Tests must be hermetic and offline: a developer's real `.env` (LLM key etc.)
must never leak into the test run. Setting FORCE_FAKE_LLM here — before any
app import — pins every test to the deterministic FakeProvider. Real-model
verification happens outside pytest (see scripts/verify_real_model.py).
"""
from __future__ import annotations

import os

os.environ["FORCE_FAKE_LLM"] = "true"
os.environ.setdefault("ENVIRONMENT", "local")
# Tests never touch the dev database: an explicit DATABASE_URL (e.g. the
# PostgreSQL test database) wins; otherwise a dedicated SQLite test file, so a
# running dev server / verification script can't lock the suite out.
os.environ.setdefault("DATABASE_URL", "sqlite:///./novel_genome_test.db")
