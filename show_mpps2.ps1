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
$proc = Get-Process Mpps -ErrorAction SilentlyContinue
if ($proc) {
    [WinAct]::ShowWindow($proc.MainWindowHandle, 9)
    [WinAct]::SetForegroundWindow($proc.MainWindowHandle)
    [WinAct]::BringWindowToTop($proc.MainWindowHandle)
}

Start-Sleep -Seconds 1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save("C:\Users\pavlo\golf5\desktop_mpps2.png", [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bmp.Dispose()
