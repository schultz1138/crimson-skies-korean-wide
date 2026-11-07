# SPDX-License-Identifier: MIT
$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '.NET Framework C# compiler not found.' }
$sources = @('InstallerEngine.cs','SelectionMigration.cs','SelectionPolicy.cs','InstallerUi.cs') |
    ForEach-Object { Join-Path $repoRoot ('source\' + $_) }
$output = Join-Path $repoRoot 'KoreanWidePatchInstaller.exe'
& $compiler /nologo /codepage:65001 /target:winexe /optimize+ /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll /r:System.Xml.dll ("/out:" + $output) $sources
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
Write-Output ('Built: ' + $output)
Write-Output 'Use tools/xdelta3.exe from the matching release ZIP to run the installer.'
