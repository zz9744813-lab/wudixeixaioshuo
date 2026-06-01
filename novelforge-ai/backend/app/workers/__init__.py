"""NovelForge AI - Worker placeholder (RQ + Celery later)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# P0: no background worker. keep for future impl.
if __name__ == "__main__":
    print("NovelForge worker – P0 not implemented yet")
