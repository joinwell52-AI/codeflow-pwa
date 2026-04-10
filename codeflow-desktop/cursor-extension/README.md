# CodeFlow Panel Launcher锛圕ursor / VS Code 鎵╁睍锛?

## 浣滅敤

- 鐘舵€佹爮鍙充晶鍑虹幇 **CodeFlow**锛岀偣鍑诲嵆鍙皾璇曞湪 **缂栬緫鍣ㄥ唴** 鎵撳紑 `http://127.0.0.1:18765/`锛堜笌鍛戒护闈㈡澘閲岀殑 **Simple Browser** 鍚岀被鑳藉姏锛夈€?
- 鑻ュ綋鍓嶇幆澧冩病鏈夊唴缃?Simple Browser 鍛戒护锛屼細閫€鍖栦负 **绯荤粺榛樿娴忚鍣?* 鎵撳紑鍚屼竴鍦板潃銆?

## 浣跨敤鍓?

璇峰厛 **杩愯 CodeFlow-Desktop.exe**锛屼繚璇佹湰鏈?`127.0.0.1:18765` 宸茬洃鍚€?

## 瀹夎锛堜换閫夛級

1. 鍦?Cursor锛?*鎵╁睍** 鈫?鍙充笂瑙?`鈥 鈫?**Install from VSIX鈥?*锛堣嫢宸叉墦鍖?`codeflow-panel-launcher-0.1.0.vsix`锛夈€?
2. 寮€鍙戝姞杞斤細 **鏂囦欢 鈫?鎵撳紑鏂囦欢澶?* 閫変腑鏈洰褰?`cursor-extension`锛屾寜 F5 浼氭柊寮€ Extension Development Host 璋冭瘯绐楀彛銆?

### 鎵撳寘 VSIX锛堥渶鏈満宸茶 `vsce`锛?

```bash
npm install -g @vscode/vsce
cd codeflow-desktop/cursor-extension
vsce package
```

## 涓庛€岀綉椤靛祵 Cursor銆嶇殑鍖哄埆

- **涓嶈兘**鍦ㄦ櫘閫氭祻瑙堝櫒椤甸潰閲屽祵鍏?Cursor 妗岄潰绐楀彛锛堣繘绋嬮殧绂伙紝娴忚鍣ㄦ棤姝?API锛夈€?
- **鍙互**鍦?Cursor 閲岀敤鍐呯疆娴忚鍣ㄥ尯鍩熸墦寮€鏈満 HTTP 闈㈡澘锛屽疄鐜般€屽崟绐楀彛閲屽乏杈逛唬鐮併€佸彸杈归潰鏉裤€嶁€斺€斾笌鏈墿灞?/ Simple Browser 涓€鑷淬€?

## 鍒嗗睆

Windows锛?*Win + 鈫?/ 鈫?* 灏?Cursor 涓庡彟涓€绐楀彛鍚勫崰鍗婂睆锛涙垨鍦?Cursor 鍐呮嫋缂栬緫鍣ㄧ粍瀹炵幇宸﹀彸鍒嗘爮銆?

