@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo ========================================
echo   Start agent-backend environment
echo ========================================
echo.

:: ---------- 1. Redis (6380) ----------
netstat -ano | find "LISTENING" | find "6380" >nul 2>&1
if errorlevel 1 (
    echo [1/4] Starting Redis on 6380 ...
    start "Redis-6380" "D:\tools\Redis\redis-server.exe" "D:\tools\Redis\redis-docker.conf"
    timeout /t 3 /nobreak >nul
) else (
    echo [1/4] Redis 6380 already running, skip
)

:: ---------- 2. Ollama (11434) ----------
netstat -ano | find "LISTENING" | find "11434" >nul 2>&1
if errorlevel 1 (
    echo [2/4] Starting Ollama ...
    start "Ollama" cmd /c "set OLLAMA_HOST=0.0.0.0:11434 && E:\Ollama\ollama.exe serve"
    timeout /t 5 /nobreak >nul
) else (
    echo [2/4] Ollama already running, skip
)

:: ---------- 3. Docker Desktop ----------
docker info >nul 2>&1
if errorlevel 1 (
    echo [3/4] ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)
echo [3/4] Docker ready

:: ---------- 4. Container ----------
docker ps -a --filter "name=^agent-backend$" --format "{{.Names}}" 2>nul | find "agent-backend" >nul
if errorlevel 1 (
    echo [4/4] Container not found, creating ...
    docker run -d --name agent-backend -p 8000:8000 ^
      -e HF_HOME=/hf_cache ^
      -e DOC_PATH=/app/docs/manual.txt ^
      -e OLLAMA_BASE_URL=http://host.docker.internal:11434 ^
      -e REDIS_HOST=host.docker.internal ^
      -e REDIS_PORT=6380 ^
      -e REDIS_PASSWORD=agent123456 ^
      -e NO_PROXY=host.docker.internal,localhost,127.0.0.1 ^
      -v "C:\Users\JaSon\.cache\huggingface:/hf_cache" ^
      -v "D:\python projects\agent\RAG2\神火股份：河南神火煤电股份有限公司内部控制管理手册.txt:/app/docs/manual.txt" ^
      -v "D:\python projects\agent\agent\多agent协作\chroma_db:/app/chroma_db" ^
      -v "D:\python projects\agent\agent\多agent协作\cache:/app/cache" ^
      agent-backend:latest
) else (
    echo [4/4] Starting existing container agent-backend ...
    docker start agent-backend >nul
)

:: ---------- Wait and open ----------
echo.
echo Waiting for service (about 10s) ...
timeout /t 10 /nobreak >nul

curl --noproxy "*" -s -o nul http://localhost:8000/health
if errorlevel 1 (
    echo [WARN] /health not responding. Check logs: docker logs --tail 30 agent-backend
) else (
    echo Service is ready
    start http://localhost:8000/docs
)

echo.
echo Done. Keep the Redis and Ollama windows open.
pause
