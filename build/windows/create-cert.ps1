# Create self-signed code-signing certificate for e-Patrol.exe
# Company: GenXAI Analytics Pvt. Ltd. | Author: MEIT SWAMI | Jaipur, Rajasthan

$ErrorActionPreference = "Stop"
$certDir = Join-Path $PSScriptRoot "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

$certName = "GenXAI Analytics Pvt. Ltd. - e-Patrol Code Signing"
$pfxPath = Join-Path $certDir "e-patrol-codesign.pfx"
$cerPath = Join-Path $certDir "e-patrol-codesign.cer"

if (Test-Path $pfxPath) {
    Write-Host "Certificate already exists: $pfxPath"
    exit 0
}

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=GenXAI Analytics Pvt. Ltd., O=GenXAI Analytics Pvt. Ltd., L=Jaipur, S=Rajasthan, C=IN" `
    -KeyAlgorithm RSA `
    -KeyLength 4096 `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date "2026-02-05").AddYears(5) `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -FriendlyName $certName `
    -TextExtension @(
        "2.5.29.37={text}1.3.6.1.5.5.7.3.3"
    )

$pwd = ConvertTo-SecureString -String "ePatrol2026!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwd | Out-Null
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null

Write-Host "Created code-signing certificate:"
Write-Host "  PFX: $pfxPath"
Write-Host "  CER: $cerPath (share with recipients to reduce SmartScreen warnings)"
Write-Host "  Password: ePatrol2026!"
Write-Host "  Valid from: 2026-02-05 | Company: GenXAI Analytics Pvt. Ltd. | Author: MEIT SWAMI"
