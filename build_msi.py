from pathlib import Path
import sys
from xml.etree import ElementTree as E
import hashlib
root=Path('dist').absolute() / 'DesktopMate'
if not root.is_dir():
    sys.exit('Build dist/DesktopMate using DesktopMate.spec first.')
ns='http://wixtoolset.org/schemas/v4/wxs'
E.register_namespace('',ns)
def el(p,t,**kw): return E.SubElement(p,'{%s}%s'%(ns,t),kw)
def ident(prefix,s): return prefix+hashlib.sha256(str(s).encode()).hexdigest()[:24]
w=E.Element('{%s}Wix'%ns)
p=el(w,'Package',Name='DesktopMate',Manufacturer='funny4875',Version='1.0.1',UpgradeCode='EDCBB2EE-477C-4DC1-99E1-6B91B4B0F6F8',Scope='perMachine')
el(p,'MajorUpgrade',DowngradeErrorMessage='A newer version of DesktopMate is already installed.')
el(p,'MediaTemplate',EmbedCab='yes')
std=el(p,'StandardDirectory',Id='ProgramFiles64Folder')
install=el(std,'Directory',Id='INSTALLFOLDER',Name='DesktopMate')
menu=el(p,'StandardDirectory',Id='ProgramMenuFolder')
desktop=el(p,'StandardDirectory',Id='DesktopFolder')
feat=el(p,'Feature',Id='Main',Title='DesktopMate',Level='1')
def walk(path,node):
    for f in sorted(path.iterdir()):
        rel=f.relative_to(root)
        if f.is_dir(): walk(f,el(node,'Directory',Id=ident('d',rel),Name=f.name))
        else:
            cid=ident('c',rel); comp=el(node,'Component',Id=cid,Guid='*'); file=el(comp,'File',Id=ident('f',rel),Source=str(f),KeyPath='yes')
            if str(rel)=='DesktopMate.exe':
                el(file,'Shortcut',Id='StartMenuShortcut',Directory='ProgramMenuFolder',Name='DesktopMate',WorkingDirectory='INSTALLFOLDER',Advertise='yes')
                el(file,'Shortcut',Id='DesktopShortcut',Directory='DesktopFolder',Name='DesktopMate',WorkingDirectory='INSTALLFOLDER',Advertise='yes')
            el(feat,'ComponentRef',Id=cid)
walk(root,install)
E.ElementTree(w).write('installer.wxs',encoding='utf-8',xml_declaration=True)
print('Files:',sum(1 for f in root.rglob('*') if f.is_file()))
