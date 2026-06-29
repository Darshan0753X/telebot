"""
queue_manager.py — Async download queue with priority support
Premium users get priority (jump ahead of free users)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from config import MAX_CONCURRENT_DOWNLOADS, QUEUE_TIMEOUT_SECONDS

log = logging.getLogger(__name__)

@dataclass(order=True)
class QueueItem:
    priority: int          # 0 = premium (higher priority), 1 = free
    seq: int               # tie-breaker (FIFO within same priority)
    user_id: int = field(compare=False)
    url: str = field(compare=False)
    fmt: str = field(compare=False)
    update: Any = field(compare=False)
    context: Any = field(compare=False)

class DownloadQueue:
    def __init__(self):
        self._queue: asyncio.PriorityQueue = None
        self._active: dict[int, bool] = {}   # user_id → is downloading
        self._seq = 0

    def _ensure_queue(self):
        if self._queue is None:
            self._queue = asyncio.PriorityQueue()

    async def add(self, user_id: int, url: str, fmt: str, update, context, priority: int = 1):
        self._ensure_queue()
        self._seq += 1
        item = QueueItem(
            priority=priority,
            seq=self._seq,
            user_id=user_id,
            url=url,
            fmt=fmt,
            update=update,
            context=context,
        )
        await self._queue.put(item)
        pos = self.position(user_id)
        log.info(f"Queued: user={user_id} fmt={fmt} priority={priority} pos={pos}")

    def position(self, user_id: int) -> int:
        """Approximate queue position (1-indexed). 0 = not in queue."""
        if self._queue is None:
            return 0
        items = list(self._queue._queue)  # internal heap
        items_sorted = sorted(items)
        for i, item in enumerate(items_sorted):
            if item.user_id == user_id:
                return i + 1
        return 0

    def size(self) -> int:
        if self._queue is None:
            return 0
        return self._queue.qsize()

    def remove(self, user_id: int) -> bool:
        """Remove user's pending item from queue."""
        if self._queue is None:
            return False
        items = list(self._queue._queue)
        original = len(items)
        items = [i for i in items if i.user_id != user_id]
        if len(items) < original:
            # Rebuild queue
            self._queue._queue.clear()
            for item in items:
                self._queue._queue.append(item)
            import heapq
            heapq.heapify(self._queue._queue)
            return True
        return False

    async def worker(self, process_fn: Callable):
        """Runs forever, processing items with concurrency limit."""
        self._ensure_queue()
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        log.info(f"Queue worker started (max concurrent: {MAX_CONCURRENT_DOWNLOADS})")

        while True:
            item: QueueItem = await self._queue.get()
            log.info(f"Processing: user={item.user_id} fmt={item.fmt}")

            async def run(i: QueueItem):
                async with semaphore:
                    try:
                        await asyncio.wait_for(
                            process_fn(i.user_id, i.url, i.fmt, i.update, i.context),
                            timeout=QUEUE_TIMEOUT_SECONDS
                        )
                    except asyncio.TimeoutError:
                        log.warning(f"Timeout: user={i.user_id}")
                        try:
                            await i.update.effective_message.reply_text(
                                "⏰ Download timed out. Please try again."
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        log.error(f"Worker error: {e}")
                    finally:
                        self._queue.task_done()

            asyncio.create_task(run(item))
