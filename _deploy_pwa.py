# -*- coding: utf-8 -*-
import paramiko, sys, os
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('120.55.164.16', username='root', password='xiaodian@ai@4009289299!', timeout=15)

sftp = ssh.open_sftp()

local_dir = r'D:\\CodeFlow\\web\pwa'
remote_dir = '/opt/codeflow/web/pwa'

for fname in os.listdir(local_dir):
    local_path = os.path.join(local_dir, fname)
    if os.path.isfile(local_path):
        remote_path = f'{remote_dir}/{fname}'
        sftp.put(local_path, remote_path)
        print(f'  uploaded: {fname}')

sftp.close()
print('PWA deploy done!')
ssh.close()
