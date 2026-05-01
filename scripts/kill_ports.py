"""Kill processes on specified ports"""
import subprocess
import sys


def kill_port(port):
    """Kill process on the given port"""
    print(f"Checking port {port}...")
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                pid = line.strip().split()[-1]
                if pid and pid != '0':
                    print(f"Killing process PID: {pid} (port {port})")
                    subprocess.run(['taskkill', '/PID', pid, '/F'],
                                   capture_output=True, timeout=5)
                    return
        print(f"Port {port} is free")
    except Exception as e:
        print(f"Port {port} check failed: {e}")


if __name__ == '__main__':
    ports = [int(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else [8000, 5173]
    for port in ports:
        kill_port(port)
