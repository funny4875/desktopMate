# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
data_files = ['index.html', 'charactor.vrm', 'charactor_v1.vrm',
              'pose.json', 'pose1.json', 'pose2.json', 'hi.json',
              'Double Peace.json', 'promptInjection.txt', 'Angry.vrma', 'Goodbye.vrma']
datas = [(str(root / name), '.') for name in data_files]
datas.append((str(root / 'VRMA'), 'VRMA'))
hiddenimports = collect_submodules('pyttsx3.drivers') + collect_submodules('google.genai')
a = Analysis([str(root / 'app.py')], pathex=[str(root)], binaries=[],
             datas=datas, hiddenimports=hiddenimports, hookspath=[],
             hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
# Qt uses Windows' ICU exports. Do not bundle a same-named Poppler ICU DLL.
a.binaries = [entry for entry in a.binaries
              if not (entry[0].lower() == 'icuuc.dll'
                      or entry[0].lower().startswith('icudt'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DesktopMate',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DesktopMate')

