# -*- coding: utf-8 -*-
import paramiko, sys, os
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('120.55.164.16', username='root', password='xiaodian@ai@4009289299!', timeout=15)

# Check where Nginx serves PWA from
_, out, _ = ssh.exec_command('grep -A5 CodeFlow /etc/nginx/sites-enabled/xiaoai 2>/dev/null | head -20', timeout=10)
print('=== Nginx config ===')
print(out.read().decode('utf-8', errors='replace'))

# Check GitHub Pages repo
_, out, _ = ssh.exec_command('ls /opt/codeflow/web/pwa/ 2>/dev/null; cat /opt/codeflow/web/pwa/config.js 2>/dev/null', timeout=10)
print('=== /opt/codeflow/web/pwa/ ===')
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
print('Done!')
