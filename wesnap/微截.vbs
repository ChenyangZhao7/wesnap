Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = "C:\Users\21165\AppData\Local\Python\bin\pythonw.exe"
sh.CurrentDirectory = base
sh.Run """" & pyw & """ """ & base & "\main.pyw""", 0, False
