import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, username_limit=5, ip_limit=20, window_seconds=300):
        self.username_limit = username_limit
        self.ip_limit = ip_limit
        self.window_seconds = window_seconds
        self.lock = threading.Lock()
        self.username_attempts = {}
        self.ip_attempts = {}

    def _prune(self, bucket, now):
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _get_bucket(self, store, key):
        bucket = store.get(key)
        if bucket is None:
            bucket = deque()
            store[key] = bucket
        return bucket

    def check_and_add(self, username, ip):
        now = time.time()
        user_key = (username or "").lower()
        ip_key = ip or ""
        with self.lock:
            user_bucket = self._get_bucket(self.username_attempts, user_key)
            ip_bucket = self._get_bucket(self.ip_attempts, ip_key)
            self._prune(user_bucket, now)
            self._prune(ip_bucket, now)
            if len(user_bucket) >= self.username_limit:
                return False, "username"
            if len(ip_bucket) >= self.ip_limit:
                return False, "ip"
            user_bucket.append(now)
            ip_bucket.append(now)
            return True, ""

    def reset_username(self, username):
        key = (username or "").lower()
        with self.lock:
            if key in self.username_attempts:
                del self.username_attempts[key]
