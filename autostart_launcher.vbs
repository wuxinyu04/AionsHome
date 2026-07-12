' Hidden launcher: starts autostart_run.bat with no console window.
' Path-agnostic — relocates with the project; rerun 开机自启_安装.bat after moving.
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run """" & dir & "\autostart_run.bat""", 0, False
