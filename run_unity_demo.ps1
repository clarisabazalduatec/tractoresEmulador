param(
    [string]$PythonExecutable = "",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$policyPath = Join-Path $repoRoot "config\qlearning_demo_policies.json"

if (-not (Test-Path -LiteralPath $policyPath)) {
    throw "No se encontro la politica entrenada: $policyPath"
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $venvPython)) {
        $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
        if ($null -ne $pyLauncher) {
            & $pyLauncher.Source -3 -m venv (Join-Path $repoRoot ".venv")
        }
        else {
            $pythonCommand = Get-Command "python" -ErrorAction Stop
            & $pythonCommand.Source -m venv (Join-Path $repoRoot ".venv")
        }

        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo crear el entorno virtual. Instala Python 3 y vuelve a ejecutar este archivo."
        }
    }

    $PythonExecutable = $venvPython
}

if (-not (Test-Path -LiteralPath $PythonExecutable)) {
    throw "No se encontro Python en la ruta indicada: $PythonExecutable"
}

Push-Location $repoRoot
try {
    $requirementsPath = Join-Path $repoRoot "requirements-unity.txt"
    $requirementsHash = (Get-FileHash -LiteralPath $requirementsPath -Algorithm SHA256).Hash
    $installedHashPath = Join-Path $repoRoot ".venv\.unity-requirements-hash"
    $installedHash = ""
    if (Test-Path -LiteralPath $installedHashPath) {
        $installedHash = (Get-Content -LiteralPath $installedHashPath -Raw).Trim()
    }

    if ($installedHash -ne $requirementsHash) {
        Write-Host "Instalando dependencias necesarias para la simulacion..."
        & $PythonExecutable -m pip install --disable-pip-version-check -r $requirementsPath
        if ($LASTEXITCODE -ne 0) {
            throw "Fallo la instalacion de dependencias desde requirements-unity.txt."
        }
        [System.IO.File]::WriteAllText($installedHashPath, $requirementsHash)
    }

    Write-Host "Iniciando los tres tractores con las politicas Q-learning incluidas."
    Write-Host "Escenario reproducible: arquitectura improved, obstaculos 10 %, semilla 0."
    Write-Host "Deja esta ventana abierta y pulsa Play en Assets/Scenes/SampleScene.unity."
    Write-Host "Servidor local: http://127.0.0.1:$Port (Ctrl+C para detener)."

    & $PythonExecutable -m src.unity_server `
        --architecture improved `
        --density 0.10 `
        --seed 0 `
        --port $Port `
        --q-policies $policyPath

    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1) {
        throw "El servidor Python termino con codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
