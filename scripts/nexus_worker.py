"""Run a real RQ worker; SpawnWorker also supports the local Windows environment."""
import os
import threading
import time
from rq import Worker
from app.nexus.jobs import redis_connection, release_due_grades


def grading_timer():
    while True:
        try:
            queued=release_due_grades()
            if queued:print(f'grading timer queued {len(queued)}',flush=True)
        except Exception as exc:
            print(f'grading timer failed: {type(exc).__name__}',flush=True)
        time.sleep(1)


if __name__=='__main__':
    if os.name=='nt':raise RuntimeError('Run the RQ Worker in Linux, WSL or Docker; Windows child monitoring is not supported')
    threading.Thread(target=grading_timer,name='grading-timer',daemon=True).start()
    worker=Worker([os.environ.get('NEXUS_QUEUE_NAME','nexus')],connection=redis_connection())
    worker.work(with_scheduler=False)
