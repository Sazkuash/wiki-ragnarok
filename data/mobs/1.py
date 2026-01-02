import os
import re

def consolidar_scripts(diretorio_entrada, arquivo_saida):
    # Regex robusta para capturar mapa, nome e ID
    regex_mob = re.compile(r'^([^,\s\t]+),.*?\s+(?:boss_)?monster\s+(.*?)\s+(\d+),', re.MULTILINE | re.IGNORECASE)

    mobs_consolidados = []

    # Verifica se o diretório existe antes de tentar ler
    if not os.path.exists(diretorio_entrada):
        print(f"ERRO: A pasta '{diretorio_entrada}' nao foi encontrada!")
        return

    print(f"Lendo arquivos em: {os.path.abspath(diretorio_entrada)}...")

    for arquivo in os.listdir(diretorio_entrada):
        if arquivo.endswith(".txt") and arquivo != arquivo_saida:
            caminho_completo = os.path.join(diretorio_entrada, arquivo)
            
            # Usando latin-1 para evitar erros de encoding comuns em scripts
            with open(caminho_completo, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
                matches = regex_mob.findall(content)
                for map_name, mob_name, mob_id in matches:
                    mob_name = mob_name.strip()
                    mobs_consolidados.append(f"Map: {map_name} | ID: {mob_id} | Name: {mob_name}")

    if not mobs_consolidados:
        print("Nenhum monstro encontrado nos arquivos .txt.")
        return

    # Remove duplicatas e ordena
    mobs_consolidados = sorted(list(set(mobs_consolidados)))

    with open(arquivo_saida, 'w', encoding='utf-8') as f_out:
        f_out.write(f"--- Relatorio Consolidado de Monstros ---\n")
        f_out.write(f"Total de spawns encontrados: {len(mobs_consolidados)}\n")
        f_out.write("-" * 50 + "\n")
        for linha in mobs_consolidados:
            f_out.write(linha + "\n")

    print(f"Sucesso! Arquivo gerado: {os.path.abspath(arquivo_saida)}")

if __name__ == "__main__":
    # Como voce esta rodando o script de DENTRO da pasta fields, use '.'
    PASTA_DOS_SCRIPTS = '.' 
    NOME_DO_ARQUIVO_FINAL = 'mobs_totais.txt'

    consolidar_scripts(PASTA_DOS_SCRIPTS, NOME_DO_ARQUIVO_FINAL)