#!/usr/bin/env python3
"""
Production-grade service starter for AgentOS
No more port locks, ever.
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.running = True

    def start_service(self, name, command, env_vars=None):
        """Start a service with proper environment"""
        env = os.environ.copy()

        # Python unbuffered for proper logging
        env['PYTHONUNBUFFERED'] = '1'

        # Add custom env vars
        if env_vars:
            env.update(env_vars)

        print(f"🚀 Starting {name}...")

        # Start process
        process = subprocess.Popen(
            command,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            # Important: Start in new process group for clean shutdown
            preexec_fn=os.setsid
        )

        self.processes[name] = process
        print(f"✅ {name} started (PID: {process.pid})")

    def stop_all(self):
        """Stop all services gracefully"""
        print("\n🛑 Stopping all services...")

        for name, process in self.processes.items():
            if process.poll() is None:  # Still running
                print(f"  Stopping {name}...")
                # Send SIGTERM to entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"  ✅ {name} stopped")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    print(f"  ⚠️  {name} force stopped")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n📡 Received signal {signum}")
        self.running = False
        self.stop_all()
        sys.exit(0)

    def monitor_services(self):
        """Monitor services and restart if needed"""
        while self.running:
            for name, process in list(self.processes.items()):
                if process.poll() is not None:
                    print(f"⚠️  {name} crashed (exit code: {process.returncode})")
                    # Restart logic here if needed

            time.sleep(5)

    def run(self):
        """Start all services"""
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        # Start Redis if not running
        if os.system("redis-cli ping > /dev/null 2>&1") != 0:
            print("🔴 Redis not running, please start it first")
            sys.exit(1)

        # Start services in order
        self.start_service(
            "websocket",
            "python3 websockets/websocket_server.py"
        )

        time.sleep(2)  # Let WebSocket start

        self.start_service(
            "api",
            "python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8001"
        )

        time.sleep(2)  # Let API start

        self.start_service(
            "workers",
            "python3 workers/worker_process.py"
        )

        self.start_service(
            "frontend",
            "cd ui-v2 && python3 -m http.server 8000"
        )

        self.start_service(
            "admin-clean",
            "cd ui-admin-clean && python3 -m http.server 8004"
        )

        print("\n✨ All services started!")
        print("\n📍 Access points:")
        print("  Frontend:    http://localhost:8000/ui-v2/")
        print("  Admin:       http://localhost:8004/")
        print("  API:         http://localhost:8001/")
        print("  API Docs:    http://localhost:8001/docs")
        print("  WebSocket:   ws://localhost:8765/")
        print("\nPress Ctrl+C to stop all services\n")

        # Monitor services
        try:
            self.monitor_services()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    manager = ServiceManager()
    manager.run()
