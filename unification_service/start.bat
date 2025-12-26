@echo off
echo ========================================
echo Service d'Unification - Demarrage
echo ========================================
echo.

REM Vérifier si Ollama est installé
where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Ollama n'est pas installe
    echo Installez Ollama depuis: https://ollama.com
    pause
    exit /b 1
)

echo [1/4] Verification d'Ollama...
ollama list | findstr "nomic-embed-text" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Telechargement du modele nomic-embed-text...
    ollama pull nomic-embed-text
)

echo [2/4] Installation des dependances Python...
pip install -r requirements.txt --quiet

echo [3/4] Demarrage du service...
start "Unification Service" python main.py

echo [4/4] Attente du service (10s)...
timeout /t 10 /nobreak >nul

echo.
echo Initialisation des mappings...
python init_mappings.py

echo.
echo ========================================
echo Service demarre sur http://localhost:8002
echo ========================================
echo.
echo Testez avec: curl http://localhost:8002/health
echo Documentation: http://localhost:8002/docs
echo.
pause
