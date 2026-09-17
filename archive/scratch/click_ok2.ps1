Add-Type @"
using System;
using System.Runtime.InteropServices;

public class Clicker2 {
    [DllImport("user32.dll")]
    public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}
"@
# Send WM_COMMAND 1 (IDOK) to dialog 199332
[Clicker2]::PostMessage([IntPtr]199332, 0x0111, (IntPtr)1, IntPtr.Zero)
