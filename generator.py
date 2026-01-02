# -*- coding: utf-8 -*-
import yaml
import os
import shutil
import re
from collections import defaultdict

# =========================
# UTILITIES
# =========================

def load_yaml_file(file_path):
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except:
        with open(file_path, "r", encoding="latin-1") as f:
            data = yaml.safe_load(f)
    return data

def parse_lua_item_info(file_path):
    item_info = {}
    if not os.path.exists(file_path): return item_info
    with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
        content = f.read()
    item_chunks = re.split(r'\[\s*(\d+)\s*\]\s*=\s*\{', content)
    for i in range(1, len(item_chunks), 2):
        item_id = int(item_chunks[i])
        block_content = item_chunks[i+1]
        name_match = re.search(r'NAME\s*=\s*["\'](.*?)["\']', block_content)
        display_name = name_match.group(1).strip() if name_match else None
        desc_match = re.search(r'DESCRICAO\s*=\s*\{(.*?)\}', block_content, re.DOTALL)
        clean_lines = []
        if desc_match:
            lines = re.findall(r'["\'](.*?)["\']', desc_match.group(1))
            for l in lines:
                l_clean = re.sub(r'\^[0-9a-fA-F]{6}', '', l).strip()
                if l_clean and "____" not in l_clean: clean_lines.append(l_clean)
        item_info[item_id] = {"name": display_name, "desc": clean_lines}
    return item_info

def safe_folder(value, default="Other"):
    if not value: return default
    value = str(value).strip()
    aliases = {
        "shadowgear": "Shadowgear", "weapon": "Weapon", "armor": "Armor",
        "etc": "Etc", "consumable": "Consumable", "card": "Card",
        "healing": "Healing", "usable": "Usable", "delayconsume": "Usable"
    }
    key = value.lower().replace("-", "").replace("_", "").replace(" ", "")
    if key in ["ammo", "petarmor"]: return None
    return aliases.get(key, value.capitalize())

def write_file(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# =========================
# MAIN GENERATOR
# =========================

def generate():
    print("--- Generating Tanelorn Chronicles Wiki (Fixing Index Files) ---")

    # 1. LOAD DATA
    mob_db_data = load_yaml_file("data/mob_db.yml")
    mobs = mob_db_data.get("Body", []) if mob_db_data else []
    
    # 2. READ LOCATIONS FROM CONSOLIDATED FILE
    mob_locations = defaultdict(set)
    consolidated_file = "data/mobs_totais.txt" 
    
    if os.path.exists(consolidated_file):
        location_pattern = re.compile(r'Map:\s*([^\s|]+).*?ID:\s*(\d+)', re.IGNORECASE)
        with open(consolidated_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = location_pattern.search(line)
                if match:
                    map_name = match.group(1).strip()
                    mob_id = int(match.group(2))
                    mob_locations[mob_id].add(map_name)
    
    # 3. LOAD TRANSLATIONS AND ITEMS
    lua_data = parse_lua_item_info("data/import_iteminfo.lua")
    droppable_items_aegis = {d["Item"] for m in mobs if m and "Drops" in m for d in m["Drops"]}

    all_items = []
    item_files = ["data/item_db_equip.yml", "data/item_db_etc.yml", "data/item_db_usable.yml"]
    for f_path in item_files:
        data = load_yaml_file(f_path)
        body = data.get("Body") if data else None
        if body:
            for i in body:
                if i and i.get("AegisName") in droppable_items_aegis:
                    if safe_folder(i.get("Type")) is not None: all_items.append(i)

    # 4. MAP LINKS
    item_path_map = {}
    aegis_to_id = {}
    for i in all_items:
        tipo, subtipo = safe_folder(i.get("Type")), safe_folder(i.get("SubType", "General"))
        item_path_map[i['Id']] = f"../items/{tipo}/{subtipo}/{i['Id']}.md"
        aegis_to_id[i['AegisName']] = i['Id']

    drops_on_item_page = defaultdict(list)
    for m in mobs:
        if m and "Drops" in m:
            for d in m["Drops"]:
                item_id = aegis_to_id.get(d["Item"])
                if item_id:
                    rate = d["Rate"]/100
                    drops_on_item_page[item_id].append(f"| [{m['Name']}](../../../monsters/{m['Id']}.md) | {rate:.2f}% |")

    # 5. CLEAR OLD DOCS
    for folder in ["items", "monsters"]:
        target_path = os.path.join("docs", folder)
        if os.path.exists(target_path): shutil.rmtree(target_path)

    write_file("docs/index.md", ["# Tanelorn Chronicles Wiki", "", "Welcome to the database."])

    # 6. GENERATE ITEMS + INDEX FILES
    tree = defaultdict(lambda: defaultdict(list))
    for i in all_items: tree[safe_folder(i.get("Type"))][safe_folder(i.get("SubType", "General"))].append(i)
    
    # Create main Item Index (docs/items/index.md)
    items_main_idx = ["# Item Database", "", "Select a category:", ""]
    for tipo in sorted(tree.keys()):
        items_main_idx.append(f"- [{tipo}]({tipo}/index.md)")
    write_file("docs/items/index.md", items_main_idx)

    for tipo, subtipos in tree.items():
        # Create Type Index (docs/items/Weapon/index.md)
        tipo_idx = [f"# {tipo}", "", "Select a sub-type:", ""]
        for s in sorted(subtipos.keys()):
            tipo_idx.append(f"- [{s}]({s}/index.md)")
        write_file(f"docs/items/{tipo}/index.md", tipo_idx)

        for subtipo, itens_lista in subtipos.items():
            # Create Subtype Index (docs/items/Weapon/Sword/index.md)
            sub_idx = [f"# {subtipo}", "", "Items:", ""]
            for i in sorted(itens_lista, key=lambda x: x["Name"]):
                sub_idx.append(f"- [{i['Name']}]({i['Id']}.md)")
                info = lua_data.get(i['Id'], {"name": i['Name'], "desc": []})
                item_page = [
                    f"# {info['name'] or i['Name']} (ID: {i['Id']})",
                    "\n## Description", "> " + "  \n> ".join(info['desc']) if info['desc'] else "*No description found.*",
                    "\n## Attributes", "| Attribute | Value |", "| :--- | :--- |", 
                    f"| Weight | {i.get('Weight', 0)/10} |", f"| Slots | {i.get('Slots', 0)} |",
                    f"| Attack | {i.get('Attack')} |" if i.get('Attack') else "",
                    f"| Defense | {i.get('Defense')} |" if i.get('Defense') else "",
                    "\n## Where to Find", "| Monster | Chance |", "| :--- | :--- |",
                    *drops_on_item_page.get(i["Id"], ["| - | Not dropped by monsters |"])
                ]
                write_file(f"docs/items/{tipo}/{subtipo}/{i['Id']}.md", item_page)
            write_file(f"docs/items/{tipo}/{subtipo}/index.md", sub_idx)

    # 7. GENERATE MONSTERS + INDEX FILE
    mobs_main_idx = ["# Monster Database", "", "| ID | Name |", "|---|---|"]
    for m in sorted(mobs, key=lambda x: x['Id'] if x else 0):
        if not m: continue
        mobs_main_idx.append(f"| {m['Id']} | [{m['Name']}]({m['Id']}.md) |")
        
        found_maps = sorted(list(mob_locations.get(int(m['Id']), [])))
        location_list_md = "\n".join([f"* {loc}" for loc in found_maps]) if found_maps else "* Special Spawn"

        m_drops = ["| Item | Chance |", "| :--- | :--- |"]
        if "Drops" in m:
            for d in m["Drops"]:
                it_id = aegis_to_id.get(d["Item"])
                it_info = lua_data.get(it_id, {"name": d["Item"]}) if it_id else {"name": d["Item"]}
                m_drops.append(f"| [{it_info['name']}]({item_path_map[it_id]}) | {d['Rate']/100:.2f}% |" if it_id else f"| {d['Item']} | {d['Rate']/100:.2f}% |")

        mob_page = [
            f"# {m['Name']} (ID: {m['Id']})", 
            "\n## Location", location_list_md,
            "\n## Status", "| Level | HP | Race | Element |", "| :--- | :--- | :--- | :--- |", 
            f"| {m.get('Level')} | {m.get('Hp')} | {m.get('Race')} | {m.get('Element')} |", 
            "\n## Drop Table", *m_drops
        ]
        write_file(f"docs/monsters/{m['Id']}.md", mob_page)
    # Create main Monster Index (docs/monsters/index.md)
    write_file("docs/monsters/index.md", mobs_main_idx)

    print("? Wiki successfully generated with all Index files.")

if __name__ == "__main__":
    generate()