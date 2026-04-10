"""从已打包的 EXE 解压 _MEIPASS，提取 panel/index.html 内容检查。"""
import sys, os, tempfile, subprocess, shutil

exe = r"D:\BridgeFlow\codeflow-desktop\dist\CodeFlow-Desktop.exe"
tmp = tempfile.mkdtemp(prefix="cf_check_")

print(f"[临时目录] {tmp}")

# 用 PyInstaller 的 pyi-archive_viewer 列举内容
r = subprocess.run(
    ["py", "-3.10", "-m", "PyInstaller.__main__", "--version"],
    capture_output=True, text=True
)
print("PyInstaller:", r.stdout.strip())

# 直接解析 PKG/CArchive（PyInstaller 单文件）
# 用 pyi-archive_viewer --log 提取
r2 = subprocess.run(
    ["py", "-3.10", "-c", f"""
import sys
sys.argv = ['pyi-archive_viewer', r'{exe}']
try:
    from PyInstaller.utils.cliutils.archive_viewer import run
    # 只是列出，不用交互
except Exception as e:
    print('import error:', e)
"""],
    capture_output=True, text=True, timeout=10
)
print(r2.stdout[:2000])
print(r2.stderr[:500])

# 最简单方法：直接运行EXE检查版本（向 HTTP 端口发请求）
import urllib.request, time
proc = subprocess.Popen([exe], creationflags=0x08000000)
time.sleep(4)
try:
    resp = urllib.request.urlopen("http://127.0.0.1:18765/api/status", timeout=3)
    data = resp.read().decode()
    print("[HTTP 响应]", data[:500])
except Exception as e:
    print("[HTTP 错误]", e)
finally:
    proc.kill()

shutil.rmtree(tmp, ignore_errors=True)
