@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "CONDA_ENV=mbs"
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=2024"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=3000"

echo Starting backend and frontend from:
echo   %ROOT_DIR%
echo.
echo If your conda env is not "%CONDA_ENV%", edit CONDA_ENV in this file first.
echo.

start "rag-server" cmd /k "cd /d ""%ROOT_DIR%server"" && conda run -n %CONDA_ENV% python -m uvicorn agent.compat_api:app --app-dir src --host %BACKEND_HOST% --port %BACKEND_PORT%"

start "rag-client" cmd /k "cd /d ""%ROOT_DIR%client"" && set ""LANGGRAPH_API_URL=http://%BACKEND_HOST%:%BACKEND_PORT%"" && set ""NEXT_PUBLIC_LANGGRAPH_API_URL=http://%FRONTEND_HOST%:%FRONTEND_PORT%/api"" && set ""NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID=assistant"" && set ""NEXT_PUBLIC_LANGGRAPH_ADMIN_ID=rag_admin"" && set ""NEXT_PUBLIC_LANGGRAPH_INGEST_ID=rag_ingest"" && set ""NEXT_PUBLIC_LANGGRAPH_DELETE_ID=rag_delete"" && set ""NEXT_PUBLIC_LANGGRAPH_REINDEX_ID=rag_reindex"" && yarn dev"

echo Backend:  http://%BACKEND_HOST%:%BACKEND_PORT%/health
echo Frontend: http://%FRONTEND_HOST%:%FRONTEND_PORT%
echo.
echo Two CMD windows have been opened.

endlocal
