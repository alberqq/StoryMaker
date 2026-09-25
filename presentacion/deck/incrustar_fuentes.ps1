# Incrusta en storymaker-propuesta.pptx las fuentes de marca (Fraunces, Inter, JetBrains Mono)
# y, si se pide, exporta un PNG por slide tal como lo pinta PowerPoint.
#
# Uso (Windows con PowerPoint instalado), desde cualquier carpeta:
#
#   powershell -ExecutionPolicy Bypass -File presentacion\deck\incrustar_fuentes.ps1
#   powershell -ExecutionPolicy Bypass -File presentacion\deck\incrustar_fuentes.ps1 -Capturas C:\ruta\png
#   powershell -ExecutionPolicy Bypass -File presentacion\deck\incrustar_fuentes.ps1 -SinIncrustar -Capturas C:\ruta\png
#
# Las TTF de fuentes/ se registran solo para la sesión (AddFontResource), sin instalarlas, y se
# retiran al terminar. PowerPoint las ve, pinta con ellas y las guarda dentro del PPTX, así que
# el deck se ve igual en un equipo que no las tenga. Si PowerPoint ya está abierto, el script no
# lo cierra.

param(
    [string]$Capturas = "",
    [switch]$SinIncrustar
)

$ErrorActionPreference = "Stop"
$deck = Split-Path -Parent $MyInvocation.MyCommand.Path
$pptx = Join-Path (Split-Path -Parent $deck) "storymaker-propuesta.pptx"
$fuentes = Get-ChildItem (Join-Path $deck "fuentes") -Filter *.ttf

Add-Type -Namespace Win32 -Name Fuentes -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)] public static extern int AddFontResourceW(string f);
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)] public static extern bool RemoveFontResourceW(string f);
[DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr h, uint m, UIntPtr w, IntPtr l, uint f, uint t, out UIntPtr r);
'@

function Avisar-Cambio {
    $r = [UIntPtr]::Zero
    [void][Win32.Fuentes]::SendMessageTimeout([IntPtr]0xffff, 0x001D, [UIntPtr]::Zero, [IntPtr]::Zero, 2, 2000, [ref]$r)
}

$yaAbierto = [bool](Get-Process POWERPNT -ErrorAction SilentlyContinue)
foreach ($f in $fuentes) { [void][Win32.Fuentes]::AddFontResourceW($f.FullName) }
Avisar-Cambio

try {
    $app = New-Object -ComObject PowerPoint.Application
    $pres = $app.Presentations.Open($pptx, $false, $false, $false)
    if ($Capturas -ne "") {
        New-Item -ItemType Directory -Force $Capturas | Out-Null
        $i = 1
        foreach ($s in $pres.Slides) {
            $s.Export((Join-Path $Capturas ("pptx-{0:D2}.png" -f $i)), "PNG", 1920, 1080)
            $i++
        }
        Write-Output ("{0} slides exportadas a {1}" -f ($i - 1), $Capturas)
    }
    if (-not $SinIncrustar) {
        $tmp = Join-Path $env:TEMP ("storymaker-propuesta-" + [guid]::NewGuid().ToString() + ".pptx")
        # 24 = ppSaveAsOpenXMLPresentation; -1 = msoTrue (EmbedTrueTypeFonts)
        $pres.SaveAs($tmp, 24, -1)
        $pres.Close()
        Copy-Item $tmp $pptx -Force
        Remove-Item $tmp -Force
        Write-Output "Fuentes incrustadas en $pptx"
    } else {
        $pres.Close()
    }
    if (-not $yaAbierto) { $app.Quit() }
}
finally {
    foreach ($f in $fuentes) { [void][Win32.Fuentes]::RemoveFontResourceW($f.FullName) }
    Avisar-Cambio
}
