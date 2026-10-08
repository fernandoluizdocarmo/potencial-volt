@echo off
chcp 65001 > nul
title Potencial Volt - Sistema de Orcamentos Eletricos
color 0A

echo ===================================================================
echo                  POTENCIAL VOLT - SISTEMA DE ORCAMENTOS
echo                    Calculo Automatico por Regiao (MG)
echo ===================================================================
echo.
echo  Iniciando o servidor local...
echo.
echo  [1] No seu COMPUTADOR: O navegador abrira automaticamente.
echo  [2] No seu TELEFONE (conectado no mesmo Wi-Fi):
echo      Acesse o link que aparecera logo abaixo na tela.
echo.
echo  Para FECHAR o programa, basta fechar esta janela.
echo ===================================================================
echo.

python app.py

pause
