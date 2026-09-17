Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class WinInspector2 {
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr parameter);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    public static string[] InspectPid(uint targetPid) {
        List<string> list = new List<string>();
        EnumWindows((hWnd, lParam) => {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (pid == targetPid) {
                StringBuilder sb = new StringBuilder(256);
                GetWindowText(hWnd, sb, 256);
                list.Add("hWnd: " + hWnd + " Visible: " + IsWindowVisible(hWnd) + " Title: '" + sb.ToString() + "'");
            }
            return true;
        }, IntPtr.Zero);
        return list.ToArray();
    }
}
"@
$proc = Get-Process Mpps -ErrorAction SilentlyContinue
if ($proc) {
    $res = [WinInspector2]::InspectPid($proc.Id)
    $res | Set-Content -Path "C:\Users\pavlo\golf5\mpps_windows.txt" -Encoding utf8
}
