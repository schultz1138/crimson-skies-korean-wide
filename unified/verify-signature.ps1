param([Parameter(Mandatory=$true)][string]$LiteralPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$signature = Get-AuthenticodeSignature -LiteralPath $LiteralPath
$certificate = $signature.SignerCertificate
$timestamp = $signature.TimeStamperCertificate
$codeSigning = $false
if ($certificate) {
    foreach ($extension in $certificate.Extensions) {
        if ($extension.Oid.Value -eq '2.5.29.37') {
            $codeSigning = @($extension.EnhancedKeyUsages | Where-Object { $_.Value -eq '1.3.6.1.5.5.7.3.3' }).Count -gt 0
        }
    }
}
$valid = $signature.Status -eq 'Valid' -and $signature.SignatureType -eq 'Authenticode' -and $null -ne $certificate -and
    $certificate.Subject -ne $certificate.Issuer -and $codeSigning -and $null -ne $timestamp
$metadata = [Diagnostics.FileVersionInfo]::GetVersionInfo((Get-Item -LiteralPath $LiteralPath).FullName)
[pscustomobject]@{
    Status=$signature.Status.ToString()
    SignatureType=$signature.SignatureType.ToString()
    Accepted=$valid
    SignerSubject=if ($certificate) {$certificate.Subject} else {$null}
    SignerThumbprint=if ($certificate) {$certificate.Thumbprint} else {$null}
    TimestampSubject=if ($timestamp) {$timestamp.Subject} else {$null}
    CodeSigningEKU=$codeSigning
    ProductName=$metadata.ProductName
    FileVersion=$metadata.FileVersion
} | ConvertTo-Json -Depth 4
if (-not $valid) { exit 1 }
