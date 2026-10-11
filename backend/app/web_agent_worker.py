from __future__ import annotations

import os
import time
from app.models.db import SessionLocal
from app.services.web_agent import run_due_sources_sync

INTERVAL = max(60, int(os.getenv("WEB_AGENT_POLL_SECONDS", "300")))
MISSION = os.getenv("WEB_AGENT_MISSION", "Discover global opportunities matching VTAB Square services")


def main():
    while True:
        db = SessionLocal()
        try:
            run_due_sources_sync(db, MISSION)
        except Exception as exc:
            print(f"web-agent-worker error: {exc}", flush=True)
        finally:
            db.close()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
