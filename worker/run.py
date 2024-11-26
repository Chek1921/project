"""Точка входа воркера.

В проде запускается четырьмя инстансами через docker-compose.
Локально удобнее так:  python -m worker.run --workers 4
"""
import argparse
import threading
import time

from worker.processor import process_one


def loop(worker_id: str, idle_sleep: float = 0.5, max_tasks: int | None = None) -> int:
    done = 0
    while max_tasks is None or done < max_tasks:
        if process_one(worker_id):
            done += 1
        else:
            if max_tasks is not None:
                break
            time.sleep(idle_sleep)
    return done


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-tasks", type=int, default=None)
    args = parser.parse_args()

    threads = [
        threading.Thread(target=loop, args=(f"w-{i + 1}", 0.5, args.max_tasks), daemon=True)
        for i in range(args.workers)
    ]
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("stopping")


if __name__ == "__main__":
    main()
