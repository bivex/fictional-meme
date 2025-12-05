#!/usr/bin/env python3
"""
High-performance launcher for the Flask Mock Server (mock_server_g.py)
Supports Gunicorn (preferred) and Flask built-in server (fallback)
"""

import warnings
warnings.filterwarnings("ignore")

import logging
import subprocess
import os
import sys
import signal
import time

# Disable unnecessary logging
logging.getLogger('werkzeug').disabled = True

try:
    import gunicorn
    HAS_GUNICORN = True
except ImportError:
    HAS_GUNICORN = False


def kill_port_processes(ports=[8000, 8001]):
    """
    Kill all processes using specified ports with SIGKILL (-9)
    Works on Linux/Unix systems using lsof
    """
    for port in ports:
        try:
            # Find processes using the port
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            pid_int = int(pid)
                            print(f"🔪 Killing process {pid_int} on port {port}")
                            os.kill(pid_int, signal.SIGKILL)
                        except (ValueError, ProcessLookupError, PermissionError) as e:
                            print(f"⚠️  Could not kill PID {pid}: {e}")
                
                # Give the OS time to release the port
                time.sleep(0.5)
        except FileNotFoundError:
            # lsof not available, try fuser as fallback
            try:
                result = subprocess.run(
                    ['fuser', '-k', '-9', f'{port}/tcp'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    print(f"🔪 Killed processes on port {port} using fuser")
                    time.sleep(0.5)
            except FileNotFoundError:
                # Neither lsof nor fuser available
                print(f"⚠️  Warning: Cannot check port {port} (lsof/fuser not found)")
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️  Error checking port {port}: {e}")


def run_gunicorn():
    """Run the server using Gunicorn (high performance)"""
    cmd = [
        "python3", "-m", "gunicorn",
        "--bind", "127.0.0.1:8000",
        "--workers", "1", # Changed from 4 to 1
        "--worker-class", "sync",
        "--timeout", "30",
        "--log-level", "debug", # Changed from critical to debug
        "--error-logfile", "gunicorn_stderr.log", # Redirect stderr to a file
        "--access-logfile", "gunicorn_stdout.log", # Redirect stdout to a file
        "mock_server_g:app"
    ]
    
    print("🚀 Starting Flask server with Gunicorn (4 workers)...")
    subprocess.run(cmd)


def run_flask():
    """Run the server using Flask built-in server (development fallback)"""
    from mock_server_g import app
    
    print("🚀 Starting Flask server (built-in, single-threaded)...")
    print("⚠️  Warning: For better performance, install Gunicorn: pip install gunicorn")
    
    app.run(
        host="127.0.0.1",
        port=8000,
        debug=False, # Enable debug mode
        threaded=True
    )


if __name__ == "__main__":
    os.environ["FLASK_ENV"] = "production" # Set to development for debug

    # Kill any processes using our ports before starting
    print("🧹 Cleaning up ports 8000 and 8001...")
    kill_port_processes([8000,8001])

    # Temporarily force Flask's built-in server for debugging
    run_flask()
