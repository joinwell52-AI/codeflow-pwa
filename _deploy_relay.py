# -*- coding: utf-8 -*-
import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('120.55.164.16', username='root', password='xiaodian@ai@4009289299!', timeout=15)

sftp = ssh.open_sftp()

# 两个路径都上传
LOCAL = r'D:\BridgeFlow\server\relay\server.py'
for remote in ['/opt/bridgeflow/relay/server.py', '/opt/bridgeflow/server.py']:
    try:
        sftp.put(LOCAL, remote)
        print(f'OK: {remote}')
    except Exception as e:
        print(f'SKIP {remote}: {e}')

sftp.close()

# 重启所有可能的服务
_, out, err = ssh.exec_command(
    'systemctl restart codeflow-relay 2>/dev/null; '
    'systemctl restart bridgeflow-relay 2>/dev/null; '
    'systemctl restart bridgeflow 2>/dev/null; '
    'sleep 2; '
    'systemctl list-units --type=service --state=running | grep -E "flow|relay"',
    timeout=20
)
print(out.read().decode('utf-8', errors='replace'))
e = err.read().decode('utf-8', errors='replace')
if e.strip():
    print('ERR:', e)
print(out.read().decode('utf-8', errors='replace'))
e = err.read().decode('utf-8', errors='replace')
if e.strip():
    print('ERR:', e)

ssh.close()
print('Done!')
