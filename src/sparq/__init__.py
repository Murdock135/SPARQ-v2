from sparq.setup import SENTINEL, setup

if not SENTINEL.exists():
    setup()
