$htmlPath = "d:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\PersonalLendingCopy\index.html"
$content = Get-Content -LiteralPath $htmlPath -Raw -Encoding UTF8
if (-not $content) { Write-Error "Failed to read HTML file"; exit 1 }
$matches = [regex]::Matches($content, 'href\s*=\s*"([^\"]+)"')
$urls = $matches | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
foreach ($url in $urls) {
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec 10 -ErrorAction Stop
        $status = $response.StatusCode
    } catch {
        $status = "ERROR"
    }
    Write-Output "$url`t$status"
}
