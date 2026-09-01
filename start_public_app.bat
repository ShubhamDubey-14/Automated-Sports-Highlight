@echo off
title AI Sports Highlights Generator - Live Public Deployment
echo ================================================================
echo    AI SPORTS HIGHLIGHTS GENERATOR - FREE PUBLIC DEPLOYMENT
echo ================================================================
echo.
echo 1. Starting local Python AI backend...
start "AI Backend Server" /min python -u app.py

echo 2. Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak >nul

echo 3. Launching Cloudflare Public HTTPS Tunnel...
echo.
echo ================================================================
echo  Your Public HTTPS link will appear below (look for trycloudflare.com)
echo  Share this link with anyone or open it in any browser/device!
echo ================================================================
echo.
npx.cmd cloudflared tunnel --url http://127.0.0.1:5000

pause
