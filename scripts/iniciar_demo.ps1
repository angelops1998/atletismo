<#
.SYNOPSIS
    Entorno de demostración local del sistema de atletismo (un solo comando).
.DESCRIPTION
    Arranca una base de datos PostgreSQL aislada (atletismo_demo), la migra al
    encabezado de Alembic, carga los datos de demostración de forma idempotente y
    levanta la aplicación FastAPI en http://127.0.0.1:8002.

    Toda la configuración se inyecta como variables de entorno del PROCESO actual:
    nunca se toca ni se sobrescribe .env, y nunca se imprime la contraseña de la
    base ni la SECRET_KEY en consola.

    Requisitos: Python y (una instalación local de PostgreSQL o Docker con el
    motor en ejecución). XAMPP (MariaDB/MySQL) NO es la base de datos de esta app.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# 0. Trabajar siempre desde la raíz del repositorio
# ---------------------------------------------------------------------------
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot

# ---------------------------------------------------------------------------
# 1. Verificar la raíz del repositorio
# ---------------------------------------------------------------------------
@(
    "app/main.py",
    "alembic.ini",
    "requirements.txt",
    ".env.example",
    "scripts/seed_demo.py"
) | ForEach-Object {
    if (-not (Test-Path -LiteralPath $_)) {
        Write-Host "[ERROR] No se encontró el archivo requerido: $_" -ForegroundColor Red
        Write-Host "Ejecuta este script desde scripts/ dentro del repositorio de atletismo." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Repositorio verificado: $repoRoot" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 2. Verificar la instalación de Python
# ---------------------------------------------------------------------------
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] No se encontró Python en el PATH. Instala Python 3.9+." -ForegroundColor Red
    exit 1
}
$pythonVersion = & python --version 2>&1
Write-Host "Python: $pythonVersion"

# ---------------------------------------------------------------------------
# 3. Localizar o crear el entorno virtual (convención del repo: .venv)
# ---------------------------------------------------------------------------
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creando entorno virtual en .venv ..."
    & python -m venv $venvDir
    if (-not $?) {
        Write-Host "[ERROR] No se pudo crear el entorno virtual." -ForegroundColor Red
        exit 1
    }
}

# Actualizar pip dentro del venv para que las instalaciones sean fiables.
& $venvPython -m pip install --upgrade pip -q | Out-Null

# ---------------------------------------------------------------------------
# 4. Verificar dependencias e instalar las que falten (solo si es necesario)
# ---------------------------------------------------------------------------
Write-Host "Verificando dependencias del proyecto ..."
$depsCheck = & $venvPython -c "
import fastapi, sqlalchemy, alembic, psycopg2, bcrypt, pydantic, uvicorn, dotenv, jose
print('deps-ok')
" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias del proyecto (requirements.txt) ..."
    & $venvPython -m pip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudieron instalar las dependencias." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Dependencias ya instaladas." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 5. Detectar base de datos PostgreSQL usable (local o Docker aislado)
# ---------------------------------------------------------------------------
$pgAvailable = $false
$pgBinary = Get-Command psql -ErrorAction SilentlyContinue
$pgService = Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" }

if ($pgBinary -or $pgService) {
    $pgAvailable = $true
    Write-Host "Se detectó una instalación local de PostgreSQL." -ForegroundColor Green
}

$dockerAvailable = $false
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    $dockerInfo = & docker info 2>$null
    if ($LASTEXITCODE -eq 0 -and $dockerInfo -match "Server:") {
        $dockerAvailable = $true
        Write-Host "Se detectó Docker con el motor en ejecución." -ForegroundColor Green
    }
}

if (-not $pgAvailable -and -not $dockerAvailable) {
    Write-Host "`n[ERROR] No se encontró una base de datos PostgreSQL disponible." -ForegroundColor Red
    Write-Host "Opciones:`n  1. Instala PostgreSQL localmente y ejecuta de nuevo este script.`n  2. Inicia Docker Desktop y ejecuta de nuevo este script (se usará un contenedor PostgreSQL aislado en localhost).`n  3. XAMPP (MariaDB/MySQL) NO es la base de datos de esta aplicación y no se usa." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# 6. Inicializar o reutilizar la base de datos demo dedicada: atletismo_demo
# ---------------------------------------------------------------------------
function Set-DemoDbEnvironment {
    param(
        [string]$ConnectionString,
        [string]$DbPassword
    )
    # Variables de entorno solo del proceso actual y sus hijos. Nunca se escriben en .env.
    $env:DATABASE_URL = $ConnectionString
    $env:DEMO_DB_PASSWORD = $DbPassword
    $env:SECRET_KEY = $script:DemoSecretKey
    $env:HTTPS_ONLY = "false"
    $env:ALGORITHM = "HS256"
    $env:ACCESS_TOKEN_EXPIRE_MINUTES = "86400"
}

# Generar (o reutilizar) la clave secreta de desarrollo, solo en memoria del proceso.
if (-not $env:SECRET_KEY) {
    $script:DemoSecretKey = & $venvPython -c "import secrets; print(secrets.token_hex(64))"
} else {
    $script:DemoSecretKey = $env:SECRET_KEY
}

$dbConnectionString = $null
$dbPassword = $null

if ($pgAvailable) {
    # --- Opción A: PostgreSQL local ---------------------------------------
    Write-Host "Usando la instalación local de PostgreSQL ..." -ForegroundColor Cyan
    $dbName = "atletismo_demo"
    $pgHost = "127.0.0.1"
    $pgPort = 5432
    $pgUser = "postgres"
    # Intento de creación de la base de datos (ignora si ya existe).
    & createdb $dbName 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "La base '$dbName' ya existe o no se pudo crear (se reutilizará si existe)." -ForegroundColor Cyan
    }
    # Si la conexión requiere contraseña, solicitarla de forma segura (no se imprime).
    $dbPassword = $null
    $testConn = & psql -d postgres -tAc "SELECT version()" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $secPwd = Read-Host -AsSecureString -Prompt "Contraseña de PostgreSQL para el usuario local (dejar vacío si usa auth de confianza)"
        if ($secPwd) {
            $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secPwd)
            try {
                $dbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
            } finally {
                [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
            }
        }
    }
    $pwdSegment = if ($dbPassword) { ":" + $dbPassword + "@" } else { "@" }
    $dbConnectionString = "postgresql://" + $pgUser + $pwdSegment + $pgHost + ":" + $pgPort + "/" + $dbName
} elseif ($dockerAvailable) {
    # --- Opción B: Docker, contenedor PostgreSQL aislado ------------------
    $containerName = "atletismo-demo-db"
    $volumeName = "atletismo-demo-pgdata"
    $pgHostPort = 5433
    $dbName = "atletismo_demo"
    $dbUser = "postgres"

    Write-Host "Preparando contenedor PostgreSQL aislado en Docker ..." -ForegroundColor Cyan

    # Reutilizar contenedor existente (detenido o en ejecución), nunca eliminar ajenos.
    $existing = & docker ps -aq --filter "name=" + $containerName 2>$null
    if ($existing) {
        $state = & docker inspect -f '{{.State.Status}}' $containerName 2>$null
        if ($state -ne "running") {
            Write-Host "Iniciando contenedor demo existente: $containerName"
            & docker start $containerName | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] No se pudo iniciar el contenedor $containerName." -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Contenedor demo ya en ejecución: $containerName"
        }
    } else {
        # Crear volumen dedicado si no existe.
        $volExists = & docker volume ls -q --filter "name=" + $volumeName 2>$null
        if (-not $volExists) {
            & docker volume create $volumeName | Out-Null
        }
        # Contraseña de la base solo en memoria del proceso, no se imprime.
        $dbPassword = (& $venvPython -c "import secrets; print(secrets.token_urlsafe(32))").Trim()
        & docker run -d `
            --name $containerName `
            --mount "type=volume,src=" + $volumeName + ",dst=/var/lib/postgresql/data" `
            -p ("127.0.0.1:" + $pgHostPort + ":5432") `
            -e ("POSTGRES_DB=" + $dbName) `
            -e ("POSTGRES_USER=" + $dbUser) `
            -e ("POSTGRES_PASSWORD=" + $dbPassword) `
            postgres:15-alpine | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] No se pudo crear el contenedor de PostgreSQL." -ForegroundColor Red
            exit 1
        }
        # Esperar a que PostgreSQL esté listo (máximo ~60 s).
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 2
            $pgReady = & docker exec $containerName pg_isready 2>$null
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        }
        if (-not $ready) {
            Write-Host "[ERROR] PostgreSQL no estuvo listo a tiempo dentro del contenedor." -ForegroundColor Red
            exit 1
        }
        Write-Host "PostgreSQL listo en el contenedor aislado." -ForegroundColor Green
    }

    $pwdSegment = if ($dbPassword) { ":" + $dbPassword + "@" } else { "@" }
    $dbConnectionString = "postgresql://" + $dbUser + $pwdSegment + "127.0.0.1:" + $pgHostPort + "/" + $dbName
}

# Exportar la conexión como variable de entorno del proceso (se hereda por hijos).
$env:DATABASE_URL = $dbConnectionString

# Validar identidad de la base antes de continuar (obligatorio).
$settingsCheck = & $venvPython -c "
from app.config import get_settings
s = get_settings()
assert 'atletismo_demo' in s.database_url, s.database_url
assert ('localhost' in s.database_url or '127.0.0.1' in s.database_url), s.database_url
print('DB_OK ' + s.database_url.split('@')[1].split('/')[0])
" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo validar la identidad de la base de datos demo." -ForegroundColor Red
    Write-Host $settingsCheck -ForegroundColor Red
    exit 1
}
$settingsCheck | ForEach-Object { if ($_ -match "^DB_OK ") { Write-Host "Base de datos verificada: " + $_.Replace('DB_OK ', '') -ForegroundColor Green } }

# Resto de variables de entorno del proceso (ya DATABASE_URL y SECRET_KEY están definidas).
$env:SECRET_KEY = $script:DemoSecretKey
$env:HTTPS_ONLY = "false"
$env:ALGORITHM = "HS256"
$env:ACCESS_TOKEN_EXPIRE_MINUTES = "86400"

# ---------------------------------------------------------------------------
# 7. Ejecutar migraciones hasta el encabezado
# ---------------------------------------------------------------------------
Write-Host "Ejecutando 'alembic upgrade head' sobre atletismo_demo ..."
& $venvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Alembic no alcanzó el encabezado." -ForegroundColor Red
    exit 1
}
Write-Host "Alembic alcanzó el encabezado (head)." -ForegroundColor Green

# ---------------------------------------------------------------------------
# 8. Ejecutar el inicializador de datos de demostración (idempotente)
# ---------------------------------------------------------------------------
Write-Host "Ejecutando el inicializador de datos de demostración (scripts/seed_demo.py) ..."
& $venvPython scripts/seed_demo.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] El inicializador de datos de demostración falló." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# 9. Iniciar la aplicación FastAPI en 127.0.0.1:8002 (bucle de primer plano)
# ---------------------------------------------------------------------------
Write-Host "`nIniciando la aplicación en http://127.0.0.1:8002 ..." -ForegroundColor Cyan
Write-Host "Presiona Ctrl+C para detener la aplicación.`n" -ForegroundColor Gray

& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8002
if (-not $?) {
    Write-Host "[ERROR] La aplicación no se inició correctamente." -ForegroundColor Red
    exit 1
}
