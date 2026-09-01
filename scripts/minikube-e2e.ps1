param(
  [string]$Namespace = 'fakebric-system',
  [int]$LocalPort = 18080,
  [string]$Python = '.venv\Scripts\python.exe'
)
$ErrorActionPreference = 'Stop'

kubectl get namespace $Namespace | Out-Null
$secret = kubectl get secret fakebric-internal -n $Namespace -o jsonpath='{.data.jwt-secret}'
if (-not $secret) { throw 'fakebric-internal jwt-secret not found' }
$jwtSecret = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($secret))
$token = & $Python -c "import jwt,sys; print(jwt.encode({'sub':'minikube-e2e','roles':['Workspace Admin']},sys.argv[1],algorithm='HS256'))" $jwtSecret
if ($LASTEXITCODE -ne 0) { throw 'could not create test JWT' }

$forward = Start-Process kubectl -ArgumentList "port-forward","svc/fakebric-api","$LocalPort`:8000","-n",$Namespace -PassThru -WindowStyle Hidden
try {
  $ready = $false
  1..30 | ForEach-Object {
    try { Invoke-WebRequest "http://127.0.0.1:$LocalPort/healthz" -UseBasicParsing | Out-Null; $ready=$true; return } catch { Start-Sleep -Seconds 1 }
  }
  if (-not $ready) { throw 'API port-forward did not become ready' }
  $headers = @{ Authorization = "Bearer $($token.Trim())" }
  $ws = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/workspaces" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"displayName":"minikube-e2e"}'
  $lh = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/workspaces/$($ws.id)/items" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"type":"Lakehouse","displayName":"e2e-lake"}'
  $table = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/lakehouses/$($lh.id)/tables" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"name":"events"}'
  Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/lakehouses/$($lh.id)/tables/events/rows" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"rows":[{"id":1,"value":"ok"}]}' | Out-Null
  $nb = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/workspaces/$($ws.id)/items" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"type":"Notebook","displayName":"e2e-notebook"}'
  $nbContent = @{nbformat=4; nbformat_minor=5; metadata=@{}; cells=@(@{cell_type='code'; execution_count=$null; metadata=@{}; outputs=@(); source="print('fakebrick-e2e-ok')"})} | ConvertTo-Json -Depth 8 -Compress
  Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/items/$($nb.id)/definition" -Method Put -Headers (@{ Authorization = "Bearer $($token.Trim())"; 'If-Match' = ([char]34 + '1' + [char]34) }) -ContentType 'application/json' -Body (@{content=($nbContent | ConvertFrom-Json)} | ConvertTo-Json -Depth 10 -Compress) | Out-Null
  $session = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/items/$($nb.id)/session" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"action":"start","timeoutSeconds":120}'
  $execution = Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/items/$($nb.id)/session/execute" -Method Post -Headers $headers -ContentType 'application/json' -Body '{}'
  $deadline=(Get-Date).AddSeconds(150); $final=$null
  do {
    Start-Sleep -Seconds 2
    $final=Invoke-RestMethod "http://127.0.0.1:$LocalPort/api/v1/items/$($nb.id)/session" -Headers $headers
    if ($final.state -eq 'FAILED') { throw "Notebook execution failed for session $($session.id)" }
  } while ($final.state -ne 'COMPLETED' -and (Get-Date) -lt $deadline)
  if ($final.state -ne 'COMPLETED') { throw "Notebook execution deadline exceeded; last state=$($final.state)" }
  $result=Invoke-WebRequest "http://127.0.0.1:$LocalPort/api/v1/items/$($nb.id)/session/result" -Headers $headers -UseBasicParsing
  if ($result.StatusCode -ne 200 -or $result.Content.Length -lt 20) { throw 'Completed session did not expose a notebook result' }
  Write-Output "E2E completed workspace=$($ws.id) lakehouse=$($lh.id) table=$($table.name) session=$($session.id) state=$($final.state)"
} finally {
  if ($forward -and -not $forward.HasExited) { Stop-Process -Id $forward.Id -Force }
}
