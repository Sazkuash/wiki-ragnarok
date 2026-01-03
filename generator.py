# -*- coding: utf-8 -*-
import yaml
import os
import shutil
import re
from collections import defaultdict

# =========================
# CONFIGURACAO DE HIERARQUIA
# =========================

def get_mapped_categories(raw_type):
    t = str(raw_type).strip()
    t_lower = t.lower()
    
    weapons_keywords = ["sword", "spear", "axe", "mace", "staff", "bow", "dagger", "katar", "book", "knuckle", "whip", "instrument"]
    for wk in weapons_keywords:
        if wk in t_lower:
            return "Weapons", t

    armor_keywords = ["armor", "headgear", "shield", "garment", "cape", "shoes", "boots", "footgear"]
    for ak in armor_keywords:
        if ak in t_lower:
            if ak in ["shoes", "boots", "footgear"]: return "Armor", "Shoes"
            if ak in ["garment", "cape"]: return "Armor", "Garment and Cape"
            return "Armor", t.title()

    if any(ck in t_lower for ck in ["healing", "usable", "recovery", "support"]):
        return "Consumables", t.title()

    return "Other", t.title()

# =========================
# UTILITIES
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
    with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))

# =========================
# GENERATOR
# =========================

def generate():
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

    # Limpeza
    for folder in ["items", "monsters"]:
        path = os.path.join("docs", folder)
        if os.path.exists(path): shutil.rmtree(path)

    print("--- 2. Gerando Paginas de Itens ---")
    tree = defaultdict(lambda: defaultdict(list))
    for it_id in ids_que_dropam:
        # Pega info do LUA ou cria padrão se falhar
        info = lua_data.get(it_id, {"name": f"Item {it_id}", "desc": [], "type": "Etc"})
        main_cat, sub_cat = get_mapped_categories(info.get("type", "Etc"))
        tree[main_cat][sub_cat].append(it_id)
        
        item_page = [
            f"# {info.get('name', f'Item {it_id}')}",
            f'\n<div class="result" markdown>',
            f"!!! abstract \"Descricao do Item (ID: {it_id})\"",
            "    " + "\n    ".join(info.get('desc', [])) if info.get('desc') else "    *Sem descricao disponivel.*",
            f'</div>',
            "\n## ?? Obtencao via Drop",
            "| Monstro | Chance |", "| :--- | :--- |",
            *(item_drop_map[it_id] if item_drop_map[it_id] else ["| - | Especial |"]),
            f"\n---", f"\n*Categoria:* {main_cat} > **{sub_cat}**"
        ]
        write_file(f"docs/items/{main_cat}/{sub_cat}/{it_id}.md", item_page)

    print("--- 3. Gerando Paginas de Monstros ---")
    for m in mobs:
        if not m: continue
        m_id = m['Id']
        m_page = [
            f"# {m['Name']} (ID: {m_id})",
            f"!!! info \"Status Basicos\"",
            f"    HP: **{m.get('Hp')}** | Level: **{m.get('Level')}** | Raca: **{m.get('Race')}**",
            "\n## ?? Tabela de Drops", "| Item | ID | Rate |", "| :--- | :--- | :--- |"
        ]
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            it_id = aegis_to_id.get(d["Item"].strip().strip('_').lower())
            if it_id:
                it_lua = lua_data.get(it_id, {"name": d["Item"], "type": "Etc"})
                m_cat, s_cat = get_mapped_categories(it_lua.get("type", "Etc"))
                m_page.append(f"| [{it_lua.get('name', d['Item'])}](../items/{m_cat}/{s_cat}/{it_id}.md) | {it_id} | {d['Rate']/100:.2f}% |")
        write_file(f"docs/monsters/{m_id}.md", m_page)

    # --- GERACAO DE INDICES VISUAIS ---
    print("--- 4. Criando Indices Visuais ---")
    
    # Home Items
    item_main_idx = ["# ?? Banco de Dados de Itens", "\n<div class=\"grid cards\" markdown>\n"]
    for mc in sorted(tree.keys()):
        item_main_idx.append(f"-   __{mc}__\n    ---\n    Listagem de {mc.lower()}.\n    [:octicons-arrow-right-24: Ver Subcategorias]({mc}/index.md)")
    item_main_idx.append("\n</div>")
    write_file("docs/items/index.md", item_main_idx)

    # Subcategorias e Listas
    for mc in tree:
        sub_idx = [f"# {mc}", "\n<div class=\"grid cards\" markdown>\n"]
        for sc in sorted(tree[mc].keys()):
            sub_idx.append(f"-   __{sc}__\n    ---\n    {len(tree[mc][sc])} itens encontrados.\n    [:octicons-arrow-right-24: Ver Lista]({sc}/index.md)")
            
            # Lista de Itens final
            it_list = [f"# Lista: {sc}", "\n| ID | Nome |", "| :--- | :--- |"]
            for iid in sorted(tree[mc][sc]):
                # Proteção contra NoneType
                it_info = lua_data.get(iid, {"name": f"Item {iid}"})
                nome_item = it_info.get("name", f"Item {iid}")
                it_list.append(f"| {iid} | [{nome_item}]({iid}.md) |")
            write_file(f"docs/items/{mc}/{sc}/index.md", it_list)
        sub_idx.append("\n</div>")
        write_file(f"docs/items/{mc}/index.md", sub_idx)

    # Indice Monstros
    m_idx = ["# ?? Bestiario", "\n| Level | Monstro | ID |", "| :---: | :--- | :---: |"]
    for m in sorted(mobs, key=lambda x: (int(str(x.get('Level', 0))) if x.get('Level') else 0, x['Id'])):
        m_idx.append(f"| {m.get('Level', 0)} | [{m['Name']}]({m['Id']}.md) | {m['Id']} |")
    write_file("docs/monsters/index.md", m_idx)

    print("Success! Wiki visual gerada.")

if __name__ == "__main__": generate()