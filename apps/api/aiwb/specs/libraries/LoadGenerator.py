# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""
Concurrent load generator for AIM inference endpoints.

Sends sustained concurrent chat completion requests to keep the running_requests
metric high enough to trigger HPA-based autoscaling. Usable both standalone
(manual testing) and as a Robot Framework library.

Standalone usage:
    uv run --project .. python libraries/LoadGenerator.py \
        --url https://aim-endpoint \
        --model "model-id" \
        --concurrency 10 \
        --max-tokens 2000 \
        --duration 120 \
        --api-key "bearer-token"
"""

import argparse
import json
import threading
import time
import uuid

import urllib3

# Suppress InsecureRequestWarning for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class _LoadSession:
    """Tracks state for a single load generation session."""

    def __init__(
        self,
        endpoint_url: str,
        model_id: str,
        concurrent_requests: int,
        max_tokens: int,
        duration_seconds: int,
        api_key: str | None,
    ):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.model_id = model_id
        self.concurrent_requests = concurrent_requests
        self.max_tokens = max_tokens
        self.duration_seconds = duration_seconds
        self.api_key = api_key

        self.load_id = str(uuid.uuid4())[:8]
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.total_sent = 0
        self.total_completed = 0
        self.total_failed = 0
        self.errors: list[str] = []
        self.threads: list[threading.Thread] = []

    def _send_requests(self, thread_id: int) -> None:
        """Worker that continuously sends requests until stopped or duration expires."""
        # Each thread gets its own connection pool
        http = urllib3.PoolManager(cert_reqs="CERT_NONE")
        url = f"{self.endpoint_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = json.dumps(
            {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a detailed technical writer. Always provide comprehensive, thorough responses.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Write a detailed 2000-word essay about the history and future of space exploration. "
                            "Cover the Mercury, Gemini, and Apollo programs. Discuss the Space Shuttle era, the "
                            "International Space Station, and modern commercial spaceflight by SpaceX and Blue Origin. "
                            "Analyze future plans for Mars colonization, asteroid mining, and interstellar travel. "
                            "Include technical details about propulsion systems, life support, and radiation shielding."
                        ),
                    },
                ],
                "max_tokens": self.max_tokens,
            }
        ).encode()

        while not self.stop_event.is_set():
            with self.lock:
                self.total_sent += 1
                request_num = self.total_sent

            try:
                resp = http.request(
                    "POST",
                    url,
                    body=body,
                    headers=headers,
                    timeout=urllib3.Timeout(connect=10, read=300),
                )
                with self.lock:
                    if resp.status == 200:
                        self.total_completed += 1
                    else:
                        self.total_failed += 1
                        body_preview = resp.data.decode("utf-8", errors="replace")[:200]
                        error_msg = f"Thread-{thread_id} req#{request_num}: HTTP {resp.status} - {body_preview}"
                        self.errors.append(error_msg)
                        self._log_error(error_msg)
            except Exception as exc:
                with self.lock:
                    self.total_failed += 1
                    error_msg = f"Thread-{thread_id} req#{request_num}: {type(exc).__name__}: {exc}"
                    self.errors.append(error_msg)
                    self._log_error(error_msg)

    def _log_error(self, error_msg: str) -> None:
        """Log error with suppression after threshold to avoid log spam."""
        error_count = len(self.errors)
        if error_count <= 5:
            _log(f"  {error_msg}")
        elif error_count == 6:
            _log("  ... suppressing further error logs (see final status for counts)")

    def start(self) -> None:
        """Spawn worker threads and schedule auto-stop after duration."""
        _log(
            f"[{self.load_id}] Starting {self.concurrent_requests} concurrent workers "
            f"against {self.endpoint_url} (model={self.model_id}, "
            f"max_tokens={self.max_tokens}, duration={self.duration_seconds}s)"
        )
        for i in range(self.concurrent_requests):
            t = threading.Thread(target=self._send_requests, args=(i,), daemon=True)
            t.start()
            self.threads.append(t)

        # Periodic status reporter
        status_thread = threading.Thread(target=self._report_status, daemon=True)
        status_thread.start()

        # Auto-stop timer
        timer = threading.Timer(self.duration_seconds, self._auto_stop)
        timer.daemon = True
        timer.start()

    def _report_status(self) -> None:
        """Periodically log load status for debugging."""
        while not self.stop_event.is_set():
            self.stop_event.wait(30)
            if not self.stop_event.is_set():
                s = self.status()
                _log(
                    f"[{self.load_id}] active={s['active_threads']}, "
                    f"sent={s['total_sent']}, completed={s['total_completed']}, "
                    f"failed={s['total_failed']}"
                )

    def _auto_stop(self) -> None:
        _log(f"[{self.load_id}] Duration expired, stopping load")
        self.stop_event.set()

    def stop(self) -> dict:
        """Signal all threads to stop and wait for them to finish."""
        self.stop_event.set()
        # Allow enough time for in-flight requests (read timeout is 300s)
        for t in self.threads:
            t.join(timeout=30)
        still_alive = sum(1 for t in self.threads if t.is_alive())
        if still_alive:
            _log(f"[{self.load_id}] Warning: {still_alive} threads still alive after stop timeout")
        return self.status()

    def status(self) -> dict:
        with self.lock:
            active = sum(1 for t in self.threads if t.is_alive())
            return {
                "load_id": self.load_id,
                "active_threads": active,
                "total_sent": self.total_sent,
                "total_completed": self.total_completed,
                "total_failed": self.total_failed,
                "total_error_count": len(self.errors),
                "errors": self.errors[:10],
            }


def _log(msg: str) -> None:
    """Log to Robot Framework logger if available, else print."""
    try:
        from robot.api import logger  # noqa: PLC0415

        logger.info(msg)
    except ImportError:
        print(msg)


class LoadGenerator:
    """Robot Framework library for generating concurrent inference load.

    Sends sustained concurrent chat completion requests to keep running_requests
    high enough to trigger autoscaling.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self._sessions: dict[str, _LoadSession] = {}

    def start_load(
        self,
        endpoint_url: str,
        model_id: str,
        concurrent_requests: int = 10,
        max_tokens: int = 2000,
        duration_seconds: int = 120,
        api_key: str | None = None,
    ) -> str:
        """Start background load generation. Returns load_id.

        Non-blocking: spawns daemon threads and returns immediately so Robot
        Framework can poll for scale-up concurrently.
        """
        session = _LoadSession(
            endpoint_url=endpoint_url,
            model_id=model_id,
            concurrent_requests=int(concurrent_requests),
            max_tokens=int(max_tokens),
            duration_seconds=int(duration_seconds),
            api_key=api_key,
        )
        session.start()
        self._sessions[session.load_id] = session
        return session.load_id

    def get_load_status(self, load_id: str) -> dict:
        """Returns current status of a load session."""
        session = self._sessions.get(load_id)
        if not session:
            raise ValueError(f"No load session with id '{load_id}'")
        return session.status()

    def stop_load(self, load_id: str) -> dict:
        """Stop a load session and return final results."""
        session = self._sessions.get(load_id)
        if not session:
            _log(f"No load session with id '{load_id}', nothing to stop")
            return {"load_id": load_id, "error": "session not found"}
        result = session.stop()
        _log(
            f"[{load_id}] Final: sent={result['total_sent']}, "
            f"completed={result['total_completed']}, "
            f"failed={result['total_failed']}"
        )
        del self._sessions[load_id]
        return result


def main():
    parser = argparse.ArgumentParser(description="Generate concurrent inference load against an AIM endpoint.")
    parser.add_argument("--url", required=True, help="AIM endpoint URL (e.g. https://aim-host)")
    parser.add_argument("--model", required=True, help="Model ID for chat completions")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests (default: 10)")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2000,
        help="Max tokens per request to keep responses slow (default: 2000)",
    )
    parser.add_argument("--duration", type=int, default=120, help="Duration in seconds (default: 120)")
    parser.add_argument("--api-key", default=None, help="Bearer token for authentication")
    args = parser.parse_args()

    gen = LoadGenerator()
    load_id = gen.start_load(
        endpoint_url=args.url,
        model_id=args.model,
        concurrent_requests=args.concurrency,
        max_tokens=args.max_tokens,
        duration_seconds=args.duration,
        api_key=args.api_key,
    )

    print(f"Load started (id={load_id}). Press Ctrl+C to stop early.\n")
    try:
        while True:
            time.sleep(5)
            status = gen.get_load_status(load_id)
            print(
                f"  active={status['active_threads']}, "
                f"sent={status['total_sent']}, "
                f"completed={status['total_completed']}, "
                f"failed={status['total_failed']}"
            )
            if status["active_threads"] == 0:
                break
    except KeyboardInterrupt:
        print("\nStopping...")

    result = gen.stop_load(load_id)
    print(f"\nFinal results: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
