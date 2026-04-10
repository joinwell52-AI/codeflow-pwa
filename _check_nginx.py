import paramiko

host = "ai.chedian.cc"
user = "root"
pwd  = "xiaodian@ai@4009289299!"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pwd, timeout=15)

cmds = [
    # 找所有 nginx 配置文件里有没有 codeflow
    "grep -r 'codeflow' /etc/nginx/ 2>/dev/null || echo 'nginx中无codeflow配置'",
    # 看 sites-enabled
    "ls /etc/nginx/sites-enabled/ 2>/dev/null || echo 'no sites-enabled'",
    # 看主配置
    "cat /etc/nginx/nginx.conf | grep -A5 -B5 'codeflow' || echo '主配置无codeflow'",
    # 5252 进程详情
    "ps aux | grep python | grep -v grep",
    # 测试本地 WebSocket 路径是否通
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5252/ || echo 'curl失败'",
]

for cmd in cmds:
    print(f"\n>>> {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=15)
    out = stdout.read().decode(errors="ignore").strip()
    err = stderr.read().decode(errors="ignore").strip()
    if out: print(out)
    if err: print("[err]", err)

client.close()
