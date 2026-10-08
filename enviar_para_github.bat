@echo off
chcp 65001 > nul
title Enviar Potencial Volt para o GitHub
color 0B

echo ========================================================
echo        ENVIAR POTENCIAL VOLT PARA O GITHUB
echo ========================================================
echo.
echo Adicionando arquivos e preparando envio...
echo.

git init
git add .
git commit -m "Publicacao Potencial Volt na Vercel"
git branch -M main

echo.
echo ========================================================
echo Conectando ao seu repositorio no GitHub...
echo (Se o repositorio ainda nao existir, crie em: github.com/new com o nome potencial-volt)
echo ========================================================
echo.

git remote remove origin 2>nul
git remote add origin https://github.com/fernandoluizdocarmo/potencial-volt.git

echo Enviando arquivos...
git push -u origin main

echo.
echo ========================================================
echo Envio concluido! Agora acesse vercel.com/new para publicar.
echo ========================================================
pause
