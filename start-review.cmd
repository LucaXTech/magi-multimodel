@echo off
call .venv\Scripts\activate.bat
python -m benchmark.review_web
pause
