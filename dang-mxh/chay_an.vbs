Set fso = CreateObject("Scripting.FileSystemObject")
d = fso.GetParentFolderName(WScript.ScriptFullName)
py = fso.GetAbsolutePathName(d & "\..\social-auto-upload\.venv\Scripts\python.exe")
CreateObject("WScript.Shell").Run """" & py & """ """ & d & "\dang_mxh.py""", 0, False
