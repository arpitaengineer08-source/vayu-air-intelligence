import sys
from src.pipeline import build
if __name__ == "__main__":
    build(live="--live" in sys.argv)
