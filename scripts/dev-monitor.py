#!/usr/bin/env python3
"""
Dev Monitor - DEVELOPMENT ONLY service watchdog

Aanvulling op Makefile die crashed services automatisch herstart via make commands.
Gebruikt make dev-api-start, make dev-frontend-start etc. voor consistent opstarten.
Start via 'make dev-monitor' - NIET VOOR PRODUCTIE.
"""

import os
import time
import requests
import subprocess
import signal
from datetime import datetime

class DevHealthMonitor:
    """Professional development health monitor voor AgentOS"""

    def __init__(self):
        self.services = {
            "api": {
                "name": "API Server",
                "health_url": "http://localhost:8001/health",
                "restart_cmd": "make dev-api-start",
                "pid_file": ".pids/api.pid",
                "max_restarts": 3,
                "restart_count": 0,
                "last_restart": None
            },
            "frontend": {
                "name": "Frontend Server",
                "health_url": "http://localhost:8000/ui-v2/",
                "restart_cmd": "make dev-frontend-start",
                "pid_file": ".pids/frontend.pid",
                "max_restarts": 3,
                "restart_count": 0,
                "last_restart": None
            },
            "admin": {
                "name": "Admin Dashboard",
                "health_url": "http://localhost:8003/",
                "restart_cmd": "make dev-admin-start",
                "pid_file": ".pids/admin.pid",
                "max_restarts": 3,
                "restart_count": 0,
                "last_restart": None
            },
            "websocket": {
                "name": "WebSocket Server",
                "health_url": None,  # WebSocket kan niet via HTTP gecheckt worden
                "restart_cmd": "make dev-websocket-start",
                "pid_file": ".pids/websocket.pid",
                "max_restarts": 3,
                "restart_count": 0,
                "last_restart": None
            }
        }

        self.running = True
        self.check_interval = 30  # seconds

        # Setup signal handlers voor graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down monitor...")
        self.running = False

    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def _is_process_running(self, pid_file: str) -> bool:
        """Check if process is running based on PID file"""
        try:
            if not os.path.exists(pid_file):
                return False

            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)
            return True

        except (FileNotFoundError, ValueError, ProcessLookupError):
            return False

    def _check_http_health(self, url: str, timeout: int = 5) -> bool:
        """Check HTTP service health"""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code < 400
        except requests.RequestException:
            return False

    def _can_restart_service(self, service_key: str) -> bool:
        """Check if service can be restarted (avoid restart loops)"""
        service = self.services[service_key]

        # Check restart count
        if service["restart_count"] >= service["max_restarts"]:
            return False

        # Check time since last restart (minimum 60 seconds)
        if service["last_restart"]:
            time_diff = time.time() - service["last_restart"]
            if time_diff < 60:
                return False

        return True

    def _restart_service(self, service_key: str):
        """Restart a crashed service"""
        service = self.services[service_key]

        if not self._can_restart_service(service_key):
            self._log(f"❌ Cannot restart {service['name']} (max restarts reached or too recent)", "WARN")
            return False

        self._log(f"🔄 Restarting {service['name']}...", "WARN")

        try:
            # Stop existing process first
            subprocess.run(f"make {service_key}-stop", shell=True, capture_output=True)
            time.sleep(2)

            # Start service
            result = subprocess.run(service["restart_cmd"], shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                service["restart_count"] += 1
                service["last_restart"] = time.time()
                self._log(f"✅ Successfully restarted {service['name']}", "INFO")
                return True
            else:
                self._log(f"❌ Failed to restart {service['name']}: {result.stderr}", "ERROR")
                return False

        except Exception as e:
            self._log(f"❌ Exception restarting {service['name']}: {e}", "ERROR")
            return False

    def _check_service_health(self, service_key: str) -> bool:
        """Check individual service health"""
        service = self.services[service_key]

        # Check if process is running
        if not self._is_process_running(service["pid_file"]):
            self._log(f"❌ {service['name']} process not running", "WARN")
            return False

        # Check HTTP health if URL provided
        if service["health_url"]:
            if not self._check_http_health(service["health_url"]):
                self._log(f"❌ {service['name']} HTTP health check failed", "WARN")
                return False

        return True

    def _reset_restart_counts(self):
        """Reset restart counts every hour for fresh start"""
        for service in self.services.values():
            if service["last_restart"] and (time.time() - service["last_restart"]) > 3600:
                service["restart_count"] = 0
                service["last_restart"] = None

    def run(self):
        """Main monitoring loop"""
        self._log("🚀 Starting AgentOS Development Health Monitor", "INFO")
        self._log(f"📊 Monitoring {len(self.services)} services every {self.check_interval}s", "INFO")

        while self.running:
            try:
                # Reset restart counts hourly
                self._reset_restart_counts()

                healthy_services = 0
                total_services = len(self.services)

                for service_key, service in self.services.items():
                    if self._check_service_health(service_key):
                        healthy_services += 1
                    else:
                        # Attempt restart
                        if self._restart_service(service_key):
                            # Wait a bit for service to start
                            time.sleep(5)

                            # Re-check health
                            if self._check_service_health(service_key):
                                healthy_services += 1

                # Status report
                if healthy_services == total_services:
                    self._log(f"✅ All services healthy ({healthy_services}/{total_services})", "INFO")
                else:
                    self._log(f"⚠️  Services status: {healthy_services}/{total_services} healthy", "WARN")

                # Sleep until next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self._log(f"❌ Monitor error: {e}", "ERROR")
                time.sleep(self.check_interval)

        self._log("🛑 Health monitor stopped", "INFO")

if __name__ == "__main__":
    monitor = DevHealthMonitor()
    monitor.run()
