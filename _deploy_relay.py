# -*- coding: utf-8 -*-
import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('120.55.164.16', username='root', password='xiaodian@ai@4009289299!', timeout=15)

sftp = ssh.open_sftp()
sftp.put(r'D:\\CodeFlow\\server\relay\server.py', '/opt/codeflow/relay/server.py')
print('server.py uploaded to /opt/codeflow/relay/')
sftp.close()

_, out, err = ssh.exec_command('systemctl restart codeflow-relay && sleep 1 && systemctl status codeflow-relay --no-pager', timeout=20)
print(out.read().decode('utf-8', errors='replace'))
e = err.read().decode('utf-8', errors='replace')
if e.strip():
    print('ERR:', e)

ssh.close()
print('Done!')
