@echo off
echo --- 1. GERANDO ARQUIVOS DA WIKI ---
python generator.py
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
echo O site estara online em:
echo https://Sazkuash.github.io/wiki-tanelorn/
pause