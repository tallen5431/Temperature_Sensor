from __future__ import annotations
import threading, time
from typing import Callable
from auto_provision import provision_probe

class AutoProvisioner(threading.Thread):
    """Background worker that keeps probes provisioned with the hub's ingest URL.

    It provisions each discovered probe by IP (preferred) with fallback to hostname.
    """
    def __init__(self, discovery, public_base_func: Callable[[], str], token: str = "", interval_ms: int = 2000, period_sec: int = 10):
        super().__init__(daemon=True)
        self.discovery = discovery
        self.public_base_func = public_base_func
        self.token = token or ""
        self.interval_ms = int(interval_ms)
        self.period_sec = int(period_sec)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        while not self._stop:
            try:
                base = (self.public_base_func() or "").rstrip("/")
                if base:
                    for p in self.discovery.list_probes().values():
                        # Handle both dict and object-style probes
                        if isinstance(p, dict):
                            host = p.get('ip') or p.get('host') or ''
                            port = int(p.get('port', 80) or 80)
                        else:
                            host = getattr(p, "ip", None) or getattr(p, "host", None) or ""
                            port = int(getattr(p, "port", 80) or 80)

                        host = host.rstrip('.')
                        if host:
                            try:
                                # Provision to <base>/api/ingest using probe IP/host
                                provision_probe(host, port, base, token=self.token, interval_ms=self.interval_ms)
                            except Exception as e:
                                # best-effort; we'll retry next cycle
                                print(f"[auto_provisioner] Failed to provision {host}:{port}: {e}")
            except Exception as e:
                print(f"[auto_provisioner] Error in provisioning cycle: {e}")
            time.sleep(self.period_sec)
