Add-Type @"
using System;
using System.Runtime.InteropServices;

public class WinAct {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);
}
"@
[WinAct]::ShowWindow([IntPtr]68260, 3) # SW_MAXIMIZE = 3, SW_RESTORE = 9
[WinAct]::SetForegroundWindow([IntPtr]68260)
[WinAct]::BringWindowToTop([IntPtr]68260)

Start-Sleep -Seconds 1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save("C:\Users\pavlo\golf5\desktop_mpps.png", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bmp.Dispose()
