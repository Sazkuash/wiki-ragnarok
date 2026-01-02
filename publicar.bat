@echo off
echo --- GERANDO NOVOS ARQUIVOS DA WIKI ---
python generator.py
echo.
echo --- SUBINDO CODIGO PARA O REPOSITORIO ---
git add .
git commit -m "Auto-update wiki"
git push origin main
echo.
echo --- PUBLICANDO SITE ONLINE ---
mkdocs gh-deploy
echo.
echo ? PROCESSO CONCLUIDO! Seu site estara online em instantes.
pause