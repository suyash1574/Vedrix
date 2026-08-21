import subprocess
import os
import sys
import time
import socket
import errno

def get_free_port(start_port):
    """Finds a free port starting from start_port."""
    port = start_port
    while port < start_port + 100:
        if _is_port_free(port):
            return port
        port += 1
    raise IOError("Could not find a free port in the specified range.")


def _is_port_free(port):
    """Check whether a port can be bound on both IPv4 and IPv6 localhost."""
    for family, addr in [(socket.AF_INET, ('127.0.0.1', port)), (socket.AF_INET6, ('::1', port))]:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                # On Windows, SO_REUSEADDR allows multiple processes to bind to the same port.
                # To accurately check if a port is in use, we must NOT use it.
                s.bind(addr)
        except OSError as exc:
            if exc.errno in (errno.EAFNOSUPPORT, errno.EINVAL, errno.ENOPROTOOPT):
                continue
            return False
    return True

def run_dev():
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")
    
    # Virtualenv python path
    if sys.platform == "win32":
        python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join(backend_dir, "venv", "bin", "python")
        
    if not os.path.exists(python_exe):
        print(f"Error: Virtual environment not found at {python_exe}")
        return

    print("--- Autergo Intelligent Launcher ---")
    
    # 1. Handle Dynamic Ports
    backend_port = get_free_port(8000)
    frontend_port = get_free_port(5173)
    
    print(f"[*] Allocating Backend to port: {backend_port}")
    print(f"[*] Allocating Frontend to port: {frontend_port}")

    # 2. Synchronize Frontend with Dynamic Backend URL
    # Vite reads .env.development.local automatically
    backend_url = f"http://localhost:{backend_port}/api/v1"
    frontend_url = f"http://localhost:{frontend_port}"
    
    env_file_path = os.path.join(frontend_dir, ".env.development.local")
    with open(env_file_path, "w") as f:
        f.write(f"VITE_API_URL={backend_url}\n")
    
    # 3. Start Backend
    # Pass FRONTEND_URL to backend so it knows where the UI is
    backend_env = os.environ.copy()
    backend_env["FRONTEND_URL"] = frontend_url
    
    backend_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(backend_port)],
        cwd=backend_dir,
        env=backend_env
    )

    # 4. Start Frontend
    # Use --port flag for Vite to respect our dynamic selection
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--port", str(frontend_port)],
        cwd=frontend_dir
    )

    print(f"\n[SUCCESS] Autergo is booting up.")
    print(f"   - API: http://localhost:{backend_port}")
    print(f"   - Web: http://localhost:{frontend_port}")
    print(f"--- Press CTRL+C to shutdown both services ---\n")

    try:
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print("Backend process terminated unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("Frontend process terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nShutting down Autergo services...")
    finally:
        # Cleanup
        if sys.platform == "win32":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(backend_process.pid)])
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)])
        else:
            backend_process.terminate()
            frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    run_dev()
