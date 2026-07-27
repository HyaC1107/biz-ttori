# statusline.ps1 (Workspace Local Version)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    $inputJson = [Console]::In.ReadToEnd()
    if ($inputJson) {
        $data = $inputJson | ConvertFrom-Json
        $model = if ($data.model) { $data.model } elseif ($data.modelName) { $data.modelName } else { "Antigravity" }
        
        $tokens = 0
        if ($data.tokens) { $tokens = $data.tokens }
        elseif ($data.usage.total_tokens) { $tokens = $data.usage.total_tokens }
        elseif ($data.totalTokens) { $tokens = $data.totalTokens }
        elseif ($data.tokenUsage) { $tokens = $data.tokenUsage }
        
        $tokenStr = if ($tokens -ge 1000) { "{0:N1}k" -f ($tokens / 1000) } else { "$tokens" }
        $now = Get-Date -Format "HH:mm:ss"
        
        Write-Output "[$model] Tokens: $tokenStr | Time: $now"
    } else {
        $now = Get-Date -Format "HH:mm:ss"
        Write-Output "[Antigravity] Time: $now"
    }
} catch {
    $now = Get-Date -Format "HH:mm:ss"
    Write-Output "[Antigravity] Time: $now"
}
