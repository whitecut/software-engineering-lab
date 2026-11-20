Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")

exePath = base & "\code\dist\HotelBooking.exe"
pywPath = base & "\code\launch_gui.pyw"

If fso.FileExists(exePath) Then
    sh.CurrentDirectory = base & "\code\dist"
    sh.Run """" & exePath & """", 1, False
ElseIf fso.FileExists(pywPath) Then
    sh.CurrentDirectory = base & "\code"
    sh.Run "pyw -3 """ & pywPath & """", 0, False
Else
    MsgBox "Launcher not found. Please check the code folder.", 16, "Hotel Booking"
End If
