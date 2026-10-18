"""
Pytest configuration for FloatChat.

- Adds the project root to sys.path so tests can import app modules directly.
- Sets a placeholder GROQ_API_KEY: several modules create a Groq client at
  import/init time; the client constructor does not call the network, so a
  placeholder key is enough to let tests exercise pure logic (SQL validation,
  region classification, float_id normalization) without any API calls.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("GROQ_API_KEY", "test-placeholder-key")