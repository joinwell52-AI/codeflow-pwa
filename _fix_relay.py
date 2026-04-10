import paramiko

host = "ai.chedian.cc"
user = "root"
pwd  = "xiaodian@ai@4009289299!"

print(f"[SSH] 连接 {user}@{host} ...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pwd, timeout=15)
print("[SSH] 连接成功")

cmds = [
    "systemctl status codeflow-relay --no-pager | head -20",
    "ss -ltnp | grep 5252 || echo '5252未监听'",
    "systemctl restart codeflow-relay",
    "sleep 2",
    "systemctl status codeflow-relay --no-pager | head -10",
    "ss -ltnp | grep 5252 || echo '5252仍未监听'",
    "nginx -t",
    "nginx -s reload",
    "echo DONE",
]

for cmd in cmds:
    print(f"\n>>> {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors="ignore").strip()
    err = stderr.read().decode(errors="ignore").strip()
    if out:
        print(out)
    if err:
        print("[stderr]", err)

client.close()
print("\n[SSH] 完成")
