@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo [.venv] 가 없습니다.
  echo 먼저 프로젝트 폴더에서 아래를 실행하세요:
  echo   py -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

echo [1/3] pip install ...
.venv\Scripts\pip install -r requirements-build.txt
if errorlevel 1 (
  echo pip 실패
  pause
  exit /b 1
)

echo [2/3] PyInstaller ^(배포용, 창 없음^) ...
.venv\Scripts\pyinstaller --noconfirm --clean coupang_keyword_analyzer.spec
if errorlevel 1 (
  echo 배포용 빌드 실패
  pause
  exit /b 1
)

echo [3/3] PyInstaller ^(디버그, 콘솔^) ...
.venv\Scripts\pyinstaller --noconfirm --clean coupang_keyword_analyzer_debug.spec
if errorlevel 1 (
  echo 디버그 빌드 실패
  pause
  exit /b 1
)

echo.
echo 완료:
echo   dist\CoupangKeywordAnalyzer.exe
echo   dist\CoupangKeywordAnalyzer_debug.exe
echo.
echo 더블클릭이 안되면 debug 버전을 실행해 콘솔 에러를 확인하세요.
echo.
pause
endlocal
