data = open(r'D:\BridgeFlow\codeflow-desktop\dist\CodeFlow-Desktop.exe','rb').read()
checks = [b'\xe6\x97\xa0\xe8\xa7\x92\xe8\x89\xb2\xe6\x95\xb0\xe6\x8d\xae', b'switchTestBody', b'steps', b'2.7.8', b'Agent']
for c in checks:
    found = c in data
    print(f"{c!r}: {'FOUND' if found else 'NOT FOUND'}")
