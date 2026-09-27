@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Roxin - mandar musica pro celular
cd /d "%~dp0"

echo.
echo   ROXIN - mandar musica pro celular
echo   ---------------------------------
echo.
echo   Suas playlists:
echo.

python empacotar.py --listar
if errorlevel 1 goto erro

echo.
echo   Escreva o nome da playlist EXATAMENTE como esta na lista.
echo   Para mandar mais de uma, separe por ponto-e-virgula:
echo      Ghibli melhores;RUN
echo.
set "escolha="
set /p escolha=  Playlist:

if "!escolha!"=="" (
  echo.
  echo   Nada escolhido. Nada foi feito.
  goto fim
)

rem monta os argumentos, cada playlist entre aspas
set "args="
set "resto=!escolha!"
:corta
for /f "tokens=1* delims=;" %%a in ("!resto!") do (
  set "um=%%a"
  set "resto=%%b"
)
rem tira espaco do comeco e do fim (nome com espaco sobrando nao acha a playlist)
for /f "tokens=* delims= " %%x in ("!um!") do set "um=%%x"
:tirafim
if not "!um!"=="" if "!um:~-1!"==" " set "um=!um:~0,-1!" & goto tirafim
if not "!um!"=="" set args=!args! "!um!"
if not "!resto!"=="" goto corta

echo.
python empacotar.py!args!
if errorlevel 1 goto erro

echo.
echo   ---------------------------------------------------------
echo   PRONTO. O arquivo esta na pasta "pacotes", aqui do lado.
echo.
echo   Agora, com a mao:
echo     1. sobe esse arquivo .zip no seu Google Drive
echo     2. no celular, abre o Drive e baixa o arquivo
echo     3. abre o Roxin, toca em "trazer musicas" e escolhe o .zip
echo   ---------------------------------------------------------
echo.
start "" "%~dp0pacotes"
goto fim

:erro
echo.
echo   Algo deu errado acima. Nada do seu acervo foi alterado --
echo   este programa so LE a pasta D:\Music, nunca escreve nela.

:fim
echo.
pause
endlocal
