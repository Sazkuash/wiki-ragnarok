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
    """
    Padroniza nomes e agrupa tipos similares para evitar duplicatas.
    """
    t = raw_type.lower().replace("_", " ").strip()
    
    # --- GRUPO ARMOR ---
    # Unifica Footgear e Boots em 'Shoes'
    armors = ["armor", "headgear", "shield", "garment", "cape", "shoes", "boots", "footgear"]
    if t in armors:
        cat_mae = "Armor"
        if t in ["garment", "cape"]:
            sub_cat = "Garment and Cape"
        elif t in ["shoes", "boots", "footgear"]:
            sub_cat = "Shoes"
        else:
            sub_cat = t.title()
        return cat_mae, sub_cat

    # --- GRUPO WEAPONS ---
    weapon_map = {
        "sword": "Swords",
        "axe": "Axe", 
        "bow": "Bow",
        "mace": "Mace",
        "staff": "Staff",
        "dagger": "Dagger",
        "spear": "Spear",
        "katar": "Katar",
        "knuckle": "Knuckle",
        "whip": "Whip",
        "instrument": "Instrument"
    }

    for key, folder in weapon_map.items():
        if key in t:
            cat_mae = "Weapons"
            # Se for espada, mantemos a divisao de maos como exemplo de organizacao
            if key == "sword":
                if "2h" in t or "two handed" in t or "two-handed" in t:
                    sub_cat = "Two-Handed Sword"
                else:
                    sub_cat = "One-Handed Sword"
            # Para o resto (Axe, Spear, etc), unificamos na pasta principal da arma
            else:
                sub_cat = folder
            return cat_mae, sub_cat
    
    # --- CONSUMIVEIS ---
    if t in ["healing", "usable", "delayconsume", "recovery", "support"]:
        return "Consumables", t.title()

    return "Other", t.title()

# =========================
# FUNCOES AUXILIARES
# =========================

def load_yaml(path):
    if not os.path.exists(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except:
        with open(path, "r", encoding="latin-1") as f:
            return yaml.safe_load(f)

def parse_lua_item_info(file_path):
    items_lua = {}
    if not os.path.exists(file_path): return items_lua
    with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
        content = f.read()
    
    # Regex para capturar blocos [ID] = { ... }
    item_chunks = re.split(r'\[\s*(\d+)\s*\]\s*=\s*\{', content)
    for i in range(1, len(item_chunks), 2):
        item_id = int(item_chunks[i])
        block = item_chunks[i+1]
        
        name_match = re.search(r'NAME\s*=\s*["\'](.*?)["\']', block)
        display_name = name_match.group(1).strip() if name_match else None
        
        desc_match = re.search(r'DESCRICAO\s*=\s*\{(.*?)\}', block, re.DOTALL)
        lines_clean = []
        found_type = "Etc"
        
        if desc_match:
            lines = re.findall(r'["\'](.*?)["\']', desc_match.group(1))
            for l in lines:
                clean_l = re.sub(r'\^[0-9a-fA-F]{6}', '', l).strip()
                if "Type:" in clean_l:
                    found_type = clean_l.split("Type:")[-1].strip()
                if clean_l and "____" not in clean_l:
                    lines_clean.append(clean_l)
        
        items_lua[item_id] = {"name": display_name, "desc": lines_clean, "type": found_type}
    return items_lua

def write_file(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# =========================
# GERADOR PRINCIPAL
# =========================

def generate():
    print("--- 1. Carregando dados do Banco de Dados ---")

    mob_db = load_yaml("data/mob_db.yml")
    mobs = mob_db.get("Body", []) if mob_db else []
    
    aegis_to_id = {}
    item_yamls = ["data/item_db_equip.yml", "data/item_db_etc.yml", "data/item_db_usable.yml"]
    for y_file in item_yamls:
        data = load_yaml(y_file)
        if data and data.get("Body"):
            for item in data["Body"]:
                if item:
                    # Limpa underscores para evitar erro de correspondencia (Boots_ vs Boots)
                    clean_aegis = item["AegisName"].strip().strip('_').lower()
                    aegis_to_id[clean_aegis] = item["Id"]

    lua_data = parse_lua_item_info("data/import_iteminfo.lua")

    # Mapeamento de Drops
    item_drop_map = defaultdict(list)
    ids_que_dropam = set()
    for m in mobs:
        if not m: continue
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            a_name = d["Item"].strip().strip('_').lower()
            it_id = aegis_to_id.get(a_name)
            if it_id:
                ids_que_dropam.add(it_id)
                rate = d["Rate"] / 100
                # Link do item para o monstro (3 niveis de pasta)
                m_link = f"| [{m['Name']}](../../../monsters/{m['Id']}.md) | {rate:.2f}% |"
                item_drop_map[it_id].append(m_link)

    # Limpar pastas antigas
    for folder in ["items", "monsters"]:
        path = os.path.join("docs", folder)
        if os.path.exists(path): shutil.rmtree(path)

    print("--- 2. Gerando paginas de Itens ---")
    tree = defaultdict(lambda: defaultdict(list))
    for it_id in ids_que_dropam:
        raw_t = lua_data.get(it_id, {}).get("type", "Etc")
        main_cat, sub_cat = get_mapped_categories(raw_t)
        tree[main_cat][sub_cat].append(it_id)
        
        info = lua_data.get(it_id, {"name": f"Item {it_id}", "desc": []})
        item_page = [
            f"# {info['name']} (ID: {it_id})",
            "\n## Description", "> " + "  \n> ".join(info['desc']) if info['desc'] else "*Sem descricao.*",
            "\n## Dropped By", "| Monster | Rate |", "| :--- | :--- |",
            *(item_drop_map[it_id] if item_drop_map[it_id] else ["| - | Obtencao Especial |"]),
            "\n---", f"\n*Localizacao:* {main_cat} > **{sub_cat}**"
        ]
        write_file(f"docs/items/{main_cat}/{sub_cat}/{it_id}.md", item_page)

    print("--- 3. Gerando paginas de Monstros ---")
    mob_locations = defaultdict(set)
    if os.path.exists("data/mobs_totais.txt"):
        with open("data/mobs_totais.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = re.search(r'Map:\s*([^\s|]+).*?ID:\s*(\d+)', line, re.I)
                if match: mob_locations[int(match.group(2))].add(match.group(1).strip())

    for m in mobs:
        if not m: continue
        m_id = m['Id']
        m_drops_table = ["| Item | ID | Rate |", "| :--- | :--- | :--- |"]
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            it_id = aegis_to_id.get(d["Item"].strip().strip('_').lower())
            if it_id:
                it_lua = lua_data.get(it_id, {"name": d["Item"], "type": "Etc"})
                m_cat, s_cat = get_mapped_categories(it_lua["type"])
                # Link do monstro para o item (1 nivel de pasta)
                link = f"[{it_lua['name']}](../items/{m_cat}/{s_cat}/{it_id}.md)"
                m_drops_table.append(f"| {link} | {it_id} | {d['Rate']/100:.2f}% |")

        locs = sorted(list(mob_locations.get(m_id, [])))
        mob_page = [f"# {m['Name']} (ID: {m_id})", "\n## Location", "\n".join([f"* {l}" for l in locs]) or "* Spawn Especial", 
                    "\n## Status", "| HP | Race | Element |", "| :--- | :--- | :--- |", f"| {m.get('Hp')} | {m.get('Race')} | {m.get('Element')} |",
                    "\n## Drop Table", *m_drops_table]
        write_file(f"docs/monsters/{m_id}.md", mob_page)

    # Gerar Indices
    write_file("docs/index.md", ["# Tanelorn Wiki", "", "- [Items](items/index.md)", "- [Monsters](monsters/index.md)"])
    
    mobs_idx = ["# Monster Database", "", "| Level | Name | ID |", "| :---: | :--- | :---: |"]
    for m in sorted(mobs, key=lambda x: (int(x.get('Level', 0)), x['Id'])):
        mobs_idx.append(f"| {m.get('Level', 0)} | [{m['Name']}]({m['Id']}.md) | {m['Id']} |")
    write_file("docs/monsters/index.md", mobs_idx)
    
    item_main_idx = ["# Item Database", ""]
    for mc in sorted(tree.keys()):
        item_main_idx.append(f"## {mc}")
        for sc in sorted(tree[mc].keys()):
            item_main_idx.append(f"- [{sc}]({mc}/{sc}/index.md)")
            sub_file = [f"# {sc}", "", "Items:", ""]
            for it_id in sorted(tree[mc][sc]):
                n = lua_data.get(it_id, {"name": str(it_id)})["name"]
                sub_file.append(f"- [{n}]({it_id}.md)")
            write_file(f"docs/items/{mc}/{sc}/index.md", sub_file)
    write_file("docs/items/index.md", item_main_idx)

    print("Success! Arquivos gerados sem erros.")

if __name__ == "__main__": generate()