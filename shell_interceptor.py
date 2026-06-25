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
    if 'ANTIGRAVITY_AGENT' in os.environ:
        return "Antigravity"
    if 'CLAUDE_CODE_SHELL' in os.environ:
        return "Claude Code"
    return "Agent"

def run_real_command(cmd_string, shell_type='cmd'):
    # Prepare env for the subprocess to avoid infinite recursion
    child_env = os.environ.copy()
    
    # Restore original system COMSPEC (usually cmd.exe on Windows)
    original_comspec = child_env.get('ORIGINAL_COMSPEC', 'cmd.exe')
    child_env['COMSPEC'] = original_comspec
    
    # Remove CLAUDE_CODE_SHELL to prevent child shell commands from going through the interceptor again
    if 'CLAUDE_CODE_SHELL' in child_env:
        del child_env['CLAUDE_CODE_SHELL']
        
    try:
        if shell_type == 'powershell':
            # Run using the real powershell executable
            powershell_path = os.path.join(
                os.environ.get('SystemRoot', 'C:\\Windows'),
                'System32\\WindowsPowerShell\\v1.0\\powershell.exe'
            )
            process = subprocess.Popen(
                [powershell_path, '-Command', cmd_string],
                env=child_env
            )
        else:
            # Popen with inherit descriptors so it handles interactive inputs, colors, etc.
            process = subprocess.Popen(
                cmd_string,
                shell=True,
                env=child_env,
                executable=original_comspec
            )
        process.wait()
        return process.returncode
    except Exception as e:
        print(f"\n[AgentGuard] Loi thuc thi lenh thuc te: {e}", file=sys.stderr)
        return 1

def main():
    args = sys.argv[1:]
    
    # Parse shell type if specified
    shell_type = 'cmd'
    if len(args) >= 2 and args[0] == '--shell':
        shell_type = args[1].lower()
        args = args[2:]
        
    if len(args) == 0:
        # Start an interactive shell session if no command arguments are passed
        original_comspec = os.environ.get('ORIGINAL_COMSPEC', 'cmd.exe')
        child_env = os.environ.copy()
        child_env['COMSPEC'] = original_comspec
        if 'CLAUDE_CODE_SHELL' in child_env:
            del child_env['CLAUDE_CODE_SHELL']
        try:
            if shell_type == 'powershell':
                powershell_path = os.path.join(
                    os.environ.get('SystemRoot', 'C:\\Windows'),
                    'System32\\WindowsPowerShell\\v1.0\\powershell.exe'
                )
                process = subprocess.Popen(
                    [powershell_path, '-NoLogo'],
                    env=child_env
                )
            else:
                process = subprocess.Popen(
                    original_comspec,
                    env=child_env
                )
            process.wait()
            sys.exit(process.returncode)
        except Exception as e:
            print(f"\n[AgentGuard] Khong the khoi dong shell tuong tac: {e}", file=sys.stderr)
            sys.exit(1)
        
    command = ""
    
    # Parse command depending on the shell type
    if shell_type == 'powershell':
        # Search for -Command or -c or -File or -f (case insensitive)
        cmd_flag_idx = -1
        for i, arg in enumerate(args):
            if arg.lower() in ('-command', '-c', '-file', '-f', '/command', '/c'):
                cmd_flag_idx = i
                break
        if cmd_flag_idx != -1 and cmd_flag_idx + 1 < len(args):
            command = args[cmd_flag_idx + 1]
        else:
            # If no flag is found, join arguments that do not start with a dash/slash
            non_flag_args = [arg for arg in args if not arg.startswith('-') and not arg.startswith('/')]
            if non_flag_args:
                command = " ".join(non_flag_args)
            else:
                command = " ".join(args)
    else:
        # Standard cmd parsing
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
        sys.exit(run_real_command(command, shell_type))
        
    # If auto-approved, run it immediately
    if status == "approved":
        sys.exit(run_real_command(command, shell_type))
        
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
                    sys.exit(run_real_command(command, shell_type))
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
