import os
import sys
import time
import requests
import subprocess

# Reconfigure standard output/error to support UTF-8 on Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Config
SERVER_URL = "http://127.0.0.1:5000"

def get_client_name():
    # Detect what agent is running this script
    # We can inspect env variables or process parents
    # Defaulting to "Agent" if not determined
    if 'CLAUDE_CODE_SHELL' in os.environ:
        return "Claude Code"
    return "Agent"

def run_real_command(cmd_string):
    # Prepare env for the subprocess to avoid infinite recursion
    child_env = os.environ.copy()
    
    # Restore original system COMSPEC (usually cmd.exe on Windows)
    original_comspec = child_env.get('ORIGINAL_COMSPEC', 'cmd.exe')
    child_env['COMSPEC'] = original_comspec
    
    # Remove CLAUDE_CODE_SHELL to prevent child shell commands from going through the interceptor again
    if 'CLAUDE_CODE_SHELL' in child_env:
        del child_env['CLAUDE_CODE_SHELL']
        
    try:
        # Popen with inherit descriptors so it handles interactive inputs, colors, etc.
        process = subprocess.Popen(
            cmd_string,
            shell=True,
            env=child_env
        )
        process.wait()
        return process.returncode
    except Exception as e:
        print(f"\n[AgentGuard] Loi thuc thi lenh thuc te: {e}", file=sys.stderr)
        return 1

def main():
    if len(sys.argv) < 2:
        print("Usage: python shell_interceptor.py [-c | /c] <command_string>", file=sys.stderr)
        sys.exit(1)
        
    args = sys.argv[1:]
    command = ""
    
    # Parse shell flags (-c for bash/sh/zsh, /c for cmd.exe)
    if args[0] in ('-c', '/c', '--command'):
        if len(args) > 1:
            command = args[1]
        else:
            command = ""
    else:
        # Fallback: join all arguments
        command = " ".join(args)
        
    command = command.strip()
    
    # Empty commands are immediately executed/ignored
    if not command:
        sys.exit(0)
        
    client = get_client_name()
    
    # Try sending approval request to server
    try:
        res = requests.post(
            f"{SERVER_URL}/api/request",
            json={"command": command, "client": client},
            timeout=2.0
        )
        res.raise_for_status()
        res_data = res.json()
        req_id = res_data.get("id")
        status = res_data.get("status")
    except Exception as e:
        # Fallback: if server is down, run the command without blocking the user
        print(f"\n[AgentGuard] Canh bao: Khong the ket noi voi may chu phe duyet ({e}).", file=sys.stderr)
        print("[AgentGuard] Tu dong chay lenh truc tiep...", file=sys.stderr)
        sys.exit(run_real_command(command))
        
    # If auto-approved, run it immediately
    if status == "approved":
        sys.exit(run_real_command(command))
        
    # Otherwise, block and poll for approval
    print(f"\n[AgentGuard] Yeu cau phe duyet lenh: {command}")
    print(f"[AgentGuard] Trang thai: Dang cho duyet tu dien thoai di dong...")
    
    resolved = False
    dots = 0
    try:
        while not resolved:
            try:
                status_res = requests.get(f"{SERVER_URL}/api/status/{req_id}", timeout=2.0)
                status_res.raise_for_status()
                status_data = status_res.json()
                current_status = status_data.get("status")
                
                if current_status == "approved":
                    print("\n[AgentGuard] Da phe duyet! [Approved] ✓ Bat dau thuc thi...")
                    resolved = True
                    sys.exit(run_real_command(command))
                elif current_status == "rejected":
                    print("\n[AgentGuard] Bi tu choi! [Rejected] ✗ Yeu cau chay lenh da bi huy.")
                    resolved = True
                    sys.exit(1)
            except requests.RequestException:
                # If network fails temporarily, keep retrying
                pass
                
            # Nice little polling animation in terminal
            dots = (dots + 1) % 4
            sys.stdout.write(f"\r[AgentGuard] Vui long phe duyet tren dien thoai{'.' * dots}{' ' * (3 - dots)}")
            sys.stdout.flush()
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\n[AgentGuard] Da huy cho phe duyet (KeyboardInterrupt). Lenh bi tu choi.")
        sys.exit(1)

if __name__ == '__main__':
    main()
