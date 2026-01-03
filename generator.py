# -*- coding: utf-8 -*-
import yaml
import os
import shutil
import re
from collections import defaultdict

# ==========================================
# 0. GERAÇÃO AUTOMÁTICA DO CONFIG (MKDOCS.YML)
# ==========================================

def generate_mkdocs_config():
    """Cria o arquivo de configuração com as extensões de Grid e Design"""
    content = """site_name: Tanelorn Chronicles Wiki
site_url: https://Sazkuash.github.io/wiki-tanelorn/
repo_url: https://github.com/Sazkuash/wiki-tanelorn

theme:
  name: material
  language: pt-BR
  palette:
    - scheme: slate
      primary: red
      accent: red
      toggle:
        icon: material/brightness-4
        name: Mudar para modo claro
    - scheme: default
      primary: red
      accent: red
      toggle:
        icon: material/brightness-7
        name: Mudar para modo escuro
  features:
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg

plugins:
  - search

nav:
  - Home: index.md
  - Items: items/index.md
  - Monsters: monsters/index.md
"""
    with open("mkdocs.yml", "w", encoding="utf-8") as f:
        f.write(content)
    print("--- 0. mkdocs.yml REGERADO COM SUCESSO ---")

# =========================
# 1. LÓGICA DE CATEGORIAS
# =========================

def get_mapped_categories(raw_type):
    t = str(raw_type).strip()
    t_lower = t.lower()
    
    weapons = ["sword", "spear", "axe", "mace", "staff", "bow", "dagger", "katar", "book", "knuckle", "whip", "instrument"]
    for wk in weapons:
        if wk in t_lower: return "Weapons", t

    armors = ["armor", "headgear", "shield", "garment", "cape", "shoes", "boots", "footgear"]
    for ak in armors:
        if ak in t_lower:
            if ak in ["shoes", "boots", "footgear"]: return "Armor", "Shoes"
            if ak in ["garment", "cape"]: return "Armor", "Garment and Cape"
            return "Armor", t.title()

    if any(ck in t_lower for ck in ["healing", "usable", "recovery", "support"]):
        return "Consumables", t.title()

    return "Other", t.title()

# =========================
# 2. UTILITÁRIOS
# =========================

def load_yaml(path):
    if not os.path.exists(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f: return yaml.safe_load(f)
    except:
        with open(path, "r", encoding="latin-1") as f: return yaml.safe_load(f)

def parse_lua_item_info(file_path):
    items_lua = {}
    if not os.path.exists(file_path): return items_lua
    with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
        content = f.read()
    item_chunks = re.split(r'\[\s*(\d+)\s*\]\s*=\s*\{', content)
    for i in range(1, len(item_chunks), 2):
        item_id = int(item_chunks[i]); block = item_chunks[i+1]
        name_match = re.search(r'NAME\s*=\s*["\'](.*?)["\']', block)
        display_name = name_match.group(1).strip() if name_match else f"Item {item_id}"
        desc_match = re.search(r'DESCRICAO\s*=\s*\{(.*?)\}', block, re.DOTALL)
        lines_clean = []; found_type = "Etc"
        if desc_match:
            lines = re.findall(r'["\'](.*?)["\']', desc_match.group(1))
            for l in lines:
                clean_l = re.sub(r'\^[0-9a-fA-F]{6}', '', l).strip()
                if "Type:" in clean_l: found_type = clean_l.split("Type:")[-1].strip()
                if clean_l and "____" not in clean_l: lines_clean.append(clean_l)
        items_lua[item_id] = {"name": display_name, "desc": lines_clean, "type": found_type}
    return items_lua

def write_file(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline='') as f:
        f.write("\n".join(lines))

# =========================
# 3. GERADOR PRINCIPAL
# =========================

def generate():
    # PASSO 0: Sempre regerar o mkdocs.yml para garantir o visual
    generate_mkdocs_config()

    print("--- 1. Carregando dados ---")
    mob_db = load_yaml("data/mob_db.yml")
    mobs = mob_db.get("Body", []) if mob_db else []
    
    aegis_to_id = {}
    for y_file in ["data/item_db_equip.yml", "data/item_db_etc.yml", "data/item_db_usable.yml"]:
        data = load_yaml(y_file)
        if data and data.get("Body"):
            for item in data["Body"]:
                if item: aegis_to_id[item["AegisName"].strip().strip('_').lower()] = item["Id"]

    lua_data = parse_lua_item_info("data/import_iteminfo.lua")
    item_drop_map = defaultdict(list)
    ids_que_dropam = set()
    
    for m in mobs:
        if not m: continue
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            it_id = aegis_to_id.get(d["Item"].strip().strip('_').lower())
            if it_id:
                ids_que_dropam.add(it_id)
                m_link = f"| [{m['Name']}](../../../monsters/{m['Id']}.md) | {d['Rate']/100:.2f}% |"
                item_drop_map[it_id].append(m_link)

    for folder in ["items", "monsters"]:
        path = os.path.join("docs", folder)
        if os.path.exists(path): shutil.rmtree(path)

    print("--- 2. Gerando Paginas de Itens ---")
    tree = defaultdict(lambda: defaultdict(list))
    for it_id in ids_que_dropam:
        info = lua_data.get(it_id, {"name": f"Item {it_id}", "desc": [], "type": "Etc"})
        main_cat, sub_cat = get_mapped_categories(info.get("type", "Etc"))
        tree[main_cat][sub_cat].append(it_id)
        
        item_page = [
            f"# {info.get('name')}",
            "",
            '<div class="result" markdown>',
            "",
            f"!!! abstract \"Descrição do Item (ID: {it_id})\"",
            "    " + "\n    ".join(info.get('desc', [])) if info.get('desc') else "    *Sem descrição.*",
            "",
            "</div>",
            "",
            "## :material-sword: Obtencao via Drop",
            "| Monstro | Chance |", "| :--- | :--- |",
            *(item_drop_map[it_id] if item_drop_map[it_id] else ["| - | Especial |"])
        ]
        write_file(f"docs/items/{main_cat}/{sub_cat}/{it_id}.md", item_page)

    print("--- 3. Gerando Paginas de Monstros ---")
    for m in mobs:
        if not m: continue
        m_page = [
            f"# {m['Name']} (ID: {m['Id']})",
            "",
            "!!! info \"Status Basicos\"",
            f"    HP: **{m.get('Hp')}** | Level: **{m.get('Level')}**",
            "",
            "## :material-treasure-chest: Drops", "| Item | ID | Rate |", "| :--- | :--- | :--- |"
        ]
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            it_id = aegis_to_id.get(d["Item"].strip().strip('_').lower())
            if it_id:
                it_lua = lua_data.get(it_id, {"name": d["Item"], "type": "Etc"})
                m_cat, s_cat = get_mapped_categories(it_lua.get("type", "Etc"))
                m_page.append(f"| [{it_lua.get('name')}](../items/{m_cat}/{s_cat}/{it_id}.md) | {it_id} | {d['Rate']/100:.2f}% |")
        write_file(f"docs/monsters/{m['Id']}.md", m_page)

    print("--- 4. Criando Indices Visuais ---")
    
    # Home (index.md)
    write_file("docs/index.md", [
        "# Tanelorn Chronicles Wiki",
        "Escolha uma categoria abaixo para navegar.",
        "",
        '<div class="grid cards" markdown>',
        "",
        "-   :material-sword: __Itens__",
        "    ---",
        "    [Acessar Banco de Dados de Itens](./items/index.md)",
        "",
        "-   :material-ghost: __Bestiário__",
        "    ---",
        "    [Ver Lista de Monstros e Drops](./monsters/index.md)",
        "",
        "</div>"
    ])

    # Indice Principal de Itens
    item_idx = ["# Banco de Dados de Itens", "", '<div class="grid cards" markdown>', ""]
    for mc in sorted(tree.keys()):
        item_idx.extend([
            f"-   __{mc}__",
            "    ---",
            f"    [:octicons-arrow-right-24: Ver Subcategorias de {mc}]({mc}/index.md)",
            ""
        ])
        
        # Subcategorias
        sub_idx = [f"# {mc}", "", '<div class="grid cards" markdown>', ""]
        for sc in sorted(tree[mc].keys()):
            sub_idx.extend([
                f"-   __{sc}__",
                "    ---",
                f"    [:octicons-arrow-right-24: Ver Lista de {sc}]({sc}/index.md)",
                ""
            ])
            
            # Lista Final
            it_list = [f"# {sc}", "", "| ID | Nome |", "| :--- | :--- |"]
            for iid in sorted(tree[mc][sc]):
                it_n = lua_data.get(iid, {'name': iid})['name']
                it_list.append(f"| {iid} | [{it_n}]({iid}.md) |")
            write_file(f"docs/items/{mc}/{sc}/index.md", it_list)
            
        sub_idx.append("</div>")
        write_file(f"docs/items/{mc}/index.md", sub_idx)
        
    item_idx.append("</div>")
    write_file("docs/items/index.md", item_idx)

    # Indice Monstros
    m_idx = ["# Bestiário", "", "| Level | Monstro | ID |", "| :---: | :--- | :---: |"]
    for m in sorted(mobs, key=lambda x: (int(str(x.get('Level', 0))) if x.get('Level') else 0, x['Id'])):
        m_idx.append(f"| {m.get('Level', 0)} | [{m['Name']}]({m['Id']}.md) | {m['Id']} |")
    write_file("docs/monsters/index.md", m_idx)

if __name__ == "__main__": generate()