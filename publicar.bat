@echo off
:: Silencia os avisos de quebra de linha do Git
git config core.autocrlf true
git config core.safecrlf false

echo --- 1. GERANDO ARQUIVOS DA WIKI E CONFIG ---
python generator.py

:: Verifica se o arquivo foi criado antes de prosseguir
if not exist mkdocs.yml (
    echo ERRO: O arquivo mkdocs.yml nao foi gerado! Verifique o script Python.
    pause
    exit
)

echo.
echo --- 2. ENVIANDO PARA O REPOSITORIO ---
git add .
git commit -m "Auto-update: %date% %time%"
git push origin main

echo.
echo --- 3. PUBLICANDO SITE ONLINE ---
mkdocs gh-deploy --force

echo.
echo PROCESSO CONCLUIDO!
echo O site estara online em breve.
pause