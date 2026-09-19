Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public class WinInspector {
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr parameter);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    public static void InspectPid(uint targetPid) {
        EnumWindows((hWnd, lParam) => {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (pid == targetPid) {
                StringBuilder sb = new StringBuilder(256);
                GetWindowText(hWnd, sb, 256);
                Console.WriteLine("hWnd: " + hWnd + " Visible: " + IsWindowVisible(hWnd) + " Title: '" + sb.ToString() + "'");
            }
            return true;
        }, IntPtr.Zero);
    }
}
"@
$proc = Get-Process Mpps -ErrorAction SilentlyContinue
if ($proc) {
    [WinInspector]::InspectPid($proc.Id) | Out-File -FilePath "C:\Users\pavlo\golf5\mpps_windows.txt" -Encoding utf8
}
