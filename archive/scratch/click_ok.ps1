Add-Type @"
using System;
using System.Runtime.InteropServices;

public class Clicker {
    [DllImport("user32.dll")]
    public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}
"@
[Clicker]::SendMessage([IntPtr]330440, 0x00F5, IntPtr.Zero, IntPtr.Zero)
