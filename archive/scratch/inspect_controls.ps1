Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class ControlInspector {
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr parameter);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public static string[] InspectChildren(IntPtr parent) {
        List<string> list = new List<string>();
        EnumChildWindows(parent, (hWnd, lParam) => {
            StringBuilder sbText = new StringBuilder(256);
            GetWindowText(hWnd, sbText, 256);
            StringBuilder sbClass = new StringBuilder(256);
            GetClassName(hWnd, sbClass, 256);
            RECT r;
            GetWindowRect(hWnd, out r);
            bool vis = IsWindowVisible(hWnd);
            list.Add(string.Format("hWnd: {0} Class: {1} Vis: {2} Rect: [{3},{4}-{5},{6}] Text: '{7}'",
                hWnd, sbClass.ToString(), vis, r.Left, r.Top, r.Right, r.Bottom, sbText.ToString()));
            return true;
        }, IntPtr.Zero);
        return list.ToArray();
    }
}
"@

$res = [ControlInspector]::InspectChildren([IntPtr]68316)
$res | Set-Content -Path "C:\Users\pavlo\golf5\mpps_controls.txt" -Encoding utf8


