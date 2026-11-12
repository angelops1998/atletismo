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

    Seguridad de credenciales:
    - La contraseña de PostgreSQL nunca se interpola en comandos de shell ni se
      incluye en DATABASE_URL. Se provee a psql mediante la variable de entorno
      PGPASSWORD (ámbito del proceso) y a Docker mediante un archivo temporal
      --env-file que se borra tras crear el contenedor.
    - La contraseña se guarda en .demo/db_pass (solo lectura, oculto, ACL
      restringida al usuario actual) para reusar el contenedor en ejecuciones
      siguientes sin tener que adivinarla.

    Requisitos: Python y (una instalación local de PostgreSQL con psql y
    createdb, o Docker con el motor en ejecución). XAMPP (MariaDB/MySQL) NO es
    la base de datos de esta app.
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
    "scripts/seed_demo.py",
    "scripts/demo_db_identity.py"
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
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudo crear el entorno virtual." -ForegroundColor Red
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 4. Verificar dependencias (no se actualiza el gestor de paquetes en cada lanza)
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
$pgPsql = Get-Command psql -ErrorAction SilentlyContinue
$pgCreatedb = Get-Command createdb -ErrorAction SilentlyContinue
$pgService = Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" }

# Se requieren AMBAS herramientas de cliente (psql y createdb), no solo una.
if ($pgPsql -and $pgCreatedb) {
    $pgAvailable = $true
    Write-Host "Se detectó una instalación local de PostgreSQL (psql + createdb)." -ForegroundColor Green
} elseif ($pgPsql -or $pgCreatedb -or $pgService) {
    Write-Host "[WARN] Se detectó PostgreSQL parcialmente pero faltan herramientas de cliente." -ForegroundColor Yellow
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
    Write-Host "Opciones:`n  1. Instala PostgreSQL localmente (psql y createdb) y ejecuta de nuevo este script.`n  2. Inicia Docker Desktop y ejecuta de nuevo este script (se usará un contenedor PostgreSQL aislado en localhost).`n  3. XAMPP (MariaDB/MySQL) NO es la base de datos de esta aplicación y no se usa." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# 6. Inicializar o reutilizar la base de datos demo dedicada: atletismo_demo
# ---------------------------------------------------------------------------
$dbName = "atletismo_demo"
$dbConnectionString = $null
$dbPassword = $null

# Directorio y archivo de credenciales solo para el contenedor Docker.
$demoDir = Join-Path $repoRoot ".demo"
$passFile = Join-Path $demoDir "db_pass"

if ($pgAvailable) {
    # --- Opción A: PostgreSQL local ---------------------------------------
    Write-Host "Usando la instalación local de PostgreSQL ..." -ForegroundColor Cyan
    $pgHost = "127.0.0.1"
    $pgPort = 5432
    $pgUser = "postgres"

    # 1. Resolver autenticación: intentar sin contraseña (auth de confianza/peer).
    $dbPassword = $null
    $testConnArgs = @("-h", $pgHost, "-p", $pgPort, "-U", $pgUser, "-d", "postgres", "-tAc", "SELECT version()")
    $testConn = & psql @testConnArgs 2>$null
    if ($LASTEXITCODE -ne 0) {
        # 2. Si falla, pedir contraseña de forma segura (no se imprime).
        $secPwd = Read-Host -AsSecureString -Prompt "Contraseña de PostgreSQL para el usuario local (dejar vacío si usa auth de confianza)"
        if ($secPwd) {
            $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secPwd)
            try {
                $dbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
            } finally {
                [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
            }
        }
        # Proveer la contraseña a psql mediante PGPASSWORD (variable de entorno
        # de ámbito del proceso), nunca como argumento de línea de comandos.
        if ($dbPassword) {
            $env:PGPASSWORD = $dbPassword
        }
        $testConn = & psql @testConnArgs 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] No se pudo conectar al servidor PostgreSQL local." -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "Conectividad con el servidor PostgreSQL local verificada." -ForegroundColor Green

    # 3. Determinar si la base de datos ya existe (consulta de catálogo).
    $sqlCheckDb = "SELECT 1 FROM pg_database WHERE datname = '" + $dbName + "'"
    $dbExistsArgs = @("-h", $pgHost, "-p", $pgPort, "-U", $pgUser, "-d", "postgres", "-tAc", $sqlCheckDb)
    $dbExists = & psql @dbExistsArgs 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudo consultar el catálogo de bases de datos." -ForegroundColor Red
        exit 1
    }
    $dbExists = ($dbExists -ne $null -and $dbExists.Trim() -eq "1")

    # 4. Crear solo si no existe y es explícitamente seguro.
    if (-not $dbExists) {
        Write-Host "Creando la base de datos '$dbName' ..." -ForegroundColor Cyan
        & createdb -h $pgHost -p $pgPort -U $pgUser $dbName 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] No se pudo crear la base de datos '$dbName'." -ForegroundColor Red
            exit 1
        }
        Write-Host "Base de datos '$dbName' creada." -ForegroundColor Green
    } else {
        Write-Host "La base de datos '$dbName' ya existe; se reutilizará." -ForegroundColor Cyan
    }

    # 5. Verificar la conexión resultante a la base demo.
    $sqlCurrentDb = "SELECT current_database()"
    $verifyArgs = @("-h", $pgHost, "-p", $pgPort, "-U", $pgUser, "-d", $dbName, "-tAc", $sqlCurrentDb)
    $verify = & psql @verifyArgs 2>$null
    if ($LASTEXITCODE -ne 0 -or ($verify -ne $null -and $verify.Trim() -ne $dbName)) {
        Write-Host "[ERROR] No se pudo verificar la conexión a la base de datos '$dbName'." -ForegroundColor Red
        exit 1
    }
    Write-Host "Conexión a '$dbName' verificada." -ForegroundColor Green

    # DATABASE_URL sin contraseña (PGPASSWORD la provee por separado).
    $dbConnectionString = "postgresql://" + $pgUser + "@" + $pgHost + ":" + $pgPort + "/" + $dbName
} elseif ($dockerAvailable) {
    # --- Opción B: Docker, contenedor PostgreSQL aislado ------------------
    $containerName = "atletismo-demo-db"
    $volumeName = "atletismo-demo-pgdata"
    $pgHostPort = 5433
    $dbUser = "postgres"

    Write-Host "Preparando contenedor PostgreSQL aislado en Docker ..." -ForegroundColor Cyan

    if (-not (Test-Path -LiteralPath $demoDir)) {
        New-Item -ItemType Directory -Path $demoDir | Out-Null
    }

    # Reutilizar contenedor existente (detenido o en ejecución), nunca eliminar ajenos.
    $filterName = "name=" + $containerName
    $existing = & docker ps -aq --filter $filterName 2>$null
    if ($existing) {
        $state = & docker inspect -f '{{.State.Status}}' $containerName 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] No se pudo inspeccionar el contenedor $containerName." -ForegroundColor Red
            exit 1
        }
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

        # Recuperar la contraseña generada originalmente para poder conectar.
        if (Test-Path -LiteralPath $passFile) {
            $dbPassword = Get-Content -LiteralPath $passFile -Raw
            $dbPassword = $dbPassword.Trim()
            if (-not $dbPassword) {
                Write-Host "[ERROR] El archivo de credenciales del contenedor está vacío." -ForegroundColor Red
                exit 1
            }
            Write-Host "Credenciales del contenedor existente recuperadas." -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Existe el contenedor $containerName pero no se encontró el archivo de credenciales ($passFile)." -ForegroundColor Red
            Write-Host "No se puede adivinar la contraseña original. Borre el contenedor manualmente o proporcione la contraseña para continuar." -ForegroundColor Red
            exit 1
        }
    } else {
        # Crear volumen dedicado si no existe.
        $filterVolume = "name=" + $volumeName
        $volExists = & docker volume ls -q --filter $filterVolume 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] No se pudo listar los volúmenes de Docker." -ForegroundColor Red
            exit 1
        }
        if (-not $volExists) {
            & docker volume create $volumeName | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] No se pudo crear el volumen dedicado $volumeName." -ForegroundColor Red
                exit 1
            }
        }
        # Contraseña de la base generada en Python, almacenada en .demo/db_pass
        # con permisos restringidos; nunca se imprime en consola.
        $dbPassword = (& $venvPython -c "import secrets; print(secrets.token_urlsafe(32))").Trim()

        # Archivo temporal para --env-file de Docker (se borra tras crear el contenedor).
        $tempCredsFile = Join-Path $demoDir ("docker_env_" + [System.Guid]::NewGuid().ToString("N") + ".tmp")
        Set-Content -LiteralPath $tempCredsFile -Value ("POSTGRES_PASSWORD=" + $dbPassword) -Encoding UTF8

        try {
            # Guardar la contraseña en el archivo persistente con ACL restringida.
            Set-Content -LiteralPath $passFile -Value $dbPassword -Encoding UTF8
            $passItem = Get-Item -LiteralPath $passFile
            $passItem.Attributes = [System.IO.FileAttributes]::ReadOnly -bor [System.IO.FileAttributes]::Hidden
            _RestringirAclAlUsuarioActual -LiteralPath $passFile

            # Construir argumentos de docker run como array para preservar
            # los límites de cada argumento (evita que PowerShell los parta).
            $mountArg = "type=volume,src=" + $volumeName + ",dst=/var/lib/postgresql/data"
            $publishArg = "127.0.0.1:" + $pgHostPort + ":5432"
            $dbEnvArg = "POSTGRES_DB=" + $dbName
            $userEnvArg = "POSTGRES_USER=" + $dbUser

            & docker run -d `
                --name $containerName `
                --mount $mountArg `
                -p $publishArg `
                --env-file $tempCredsFile `
                -e $dbEnvArg `
                -e $userEnvArg `
                postgres:15-alpine | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] No se pudo crear el contenedor de PostgreSQL." -ForegroundColor Red
                exit 1
            }
        } finally {
            # Borrar el archivo temporal de credenciales inmediatamente.
            if (Test-Path -LiteralPath $tempCredsFile) {
                Remove-Item -LiteralPath $tempCredsFile -Force
            }
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

    # DATABASE_URL sin contraseña (PGPASSWORD la provee por separado).
    $dbConnectionString = "postgresql://" + $dbUser + "@127.0.0.1:" + $pgHostPort + "/" + $dbName
}

# Exportar la conexión como variable de entorno del proceso (se hereda por hijos).
# Nunca se escribe en .env ni se imprime. La contraseña viaja por PGPASSWORD.
$env:DATABASE_URL = $dbConnectionString

# Proveer PGPASSWORD a todos los procesos hijos (psql, SQLAlchemy/psycopg2).
if ($dbPassword) {
    $env:PGPASSWORD = $dbPassword
}

# Generar (o reutilizar) la clave secreta de desarrollo, solo en memoria del proceso.
if (-not $env:SECRET_KEY) {
    $script:DemoSecretKey = & $venvPython -c "import secrets; print(secrets.token_hex(64))"
    $env:SECRET_KEY = $script:DemoSecretKey
} else {
    $script:DemoSecretKey = $env:SECRET_KEY
}

# Resto de variables de entorno del proceso (ya DATABASE_URL, PGPASSWORD y SECRET_KEY están definidas).
$env:HTTPS_ONLY = "false"
$env:ALGORITHM = "HS256"
$env:ACCESS_TOKEN_EXPIRE_MINUTES = "86400"

# ---------------------------------------------------------------------------
# 6b. Validar identidad REAL de la base antes de cualquier escritura (Alembic).
#     No se ejecuta Alembic hasta que la identidad del servidor conectado se
#     haya verificado positivamente contra atletismo_demo.
# ---------------------------------------------------------------------------
Write-Host "Verificando identidad real de la base de datos conectada ..." -ForegroundColor Cyan
$identityCheck = & $venvPython scripts/demo_db_identity.py --verify-connection 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo verificar la identidad de la base de datos demo." -ForegroundColor Red
    # Sanitizar: no mostrar la URL completa (podría contener credenciales).
    $identityCheck | ForEach-Object { if ($_ -notmatch 'postgresql://') { Write-Host $_ -ForegroundColor Red } }
    exit 1
}
$identityCheck | ForEach-Object { if ($_ -eq "DB_OK") { Write-Host "Base de datos verificada (atletismo_demo, localhost, PostgreSQL)." -ForegroundColor Green } }

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
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] La aplicación no se inició correctamente." -ForegroundColor Red
    exit 1
}


# ---------------------------------------------------------------------------
# Función auxiliar: restringe el ACL de un archivo al usuario actual.
# ---------------------------------------------------------------------------
function _RestringirAclAlUsuarioActual {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath
    )

    $acl = Get-ACL -LiteralPath $LiteralPath
    $acl.SetAccessRuleProtection($true, $false)  # Desheredar, copiar existentes
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $currentUser, "FullControl", "Allow"
    )
    $acl.SetAccessRule($rule)
    Set-ACL -LiteralPath $LiteralPath -AclObject $acl
}
