# URL Extraction and Validation Script
# Pavel Shchelkanogov - 2026

$htmlPath = "$PSScriptRoot\index.html"
if (-not (Test-Path $htmlPath)) {
    Write-Error "Could not find index.html in $PSScriptRoot"
    exit 1
}

Write-Host "--- URL Extraction & Validation Tools ---" -ForegroundColor Cyan
Write-Host "Target: $htmlPath"

$content = Get-Content $htmlPath -Raw
# Regex to find href="..." and src="..."
$regex = '(?:href|src)\s*=\s*"([^"]+)"'
$matches = [regex]::Matches($content, $regex)

# Filter and clean URLs
$urls = $matches | ForEach-Object { $_.Groups[1].Value } | Where-Object { 
    $_ -match '^https?://' -and $_ -notmatch 'localhost'
} | Sort-Object -Unique

Write-Host "Found $($urls.Count) unique external URLs to check.`n"

$results = @()

foreach ($url in $urls) {
    Write-Host "Checking: $url ... " -NoNewline
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec 10 -ErrorAction Stop -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -UseBasicParsing
        $statusCode = [int]$response.StatusCode
        $statusMessage = "OK"
        Write-Host "[$statusCode]" -ForegroundColor Green
    } catch {
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        $statusMessage = "FAILED"
        Write-Host "[$statusCode] - $($_.Exception.Message)" -ForegroundColor Red
    }
    
    $results += [PSCustomObject]@{
        URL        = $url
        Status     = $statusMessage
        StatusCode = $statusCode
    }
}

Write-Host "`n--- Summary ---" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$brokenCount = ($results | Where-Object { $_.Status -eq "FAILED" }).Count
if ($brokenCount -gt 0) {
    Write-Host "`nWARNING: Found $brokenCount broken links!" -ForegroundColor Yellow
} else {
    Write-Host "`nSuccess: All links are valid." -ForegroundColor Green
}

# Write-Host "`nPress Enter to exit"
