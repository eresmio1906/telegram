Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

currentPath = FSO.GetParentFolderName(WScript.ScriptFullName)

WshShell.Run Chr(34) & currentPath & "\runner.bat" & Chr(34), 1

Set FSO = Nothing
Set WshShell = Nothing