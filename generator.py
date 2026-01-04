# -*- coding: utf-8 -*-
import yaml
import os
import shutil
import re
from collections import defaultdict

# =========================
# 0. DESIGN & UI CONFIG
# =========================

def generate_full_assets():
    for folder in ["docs/items", "docs/monsters", "docs/stylesheets"]:
        os.makedirs(folder, exist_ok=True)

    config_path = "mkdocs.yml"
    mkdocs_content = """site_name: Tanelorn Wiki
site_url: https://Sazkuash.github.io/wiki-tanelorn/
theme:
  name: material
  language: en
  palette:
    - scheme: slate
      primary: black
      accent: red
  features:
    - navigation.tabs
    - navigation.top
    - search.suggest
    - search.highlight

extra_css:
  - stylesheets/custom.css

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg

nav:
  - Home: index.md
  - Items: items/index.md
  - Monsters: monsters/index.md
"""
    with open(config_path, "w", encoding="utf-8") as f: f.write(mkdocs_content)

    css_content = """
:root {
  --md-primary-fg-color: #000000;
  --md-accent-fg-color: #ff0000;
  --card-bg: linear-gradient(145deg, #1a1a1a, #0f0f0f);
}
.grid.cards > ul {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  list-style: none !important;
  padding: 0 !important;
}
.grid.cards > ul > li {
  background: var(--card-bg) !important;
  border: 1px solid #2a2a2a !important;
  border-radius: 4px !important;
  transition: all 0.25s ease;
}
.grid.cards > ul > li:hover {
  border-color: #ff0000 !important;
  transform: translateY(-3px);
  box-shadow: 0 0 15px rgba(255, 0, 0, 0.4);
}
.grid.cards a {
  display: flex !important;
  align-items: center;
  justify-content: center;
  padding: 25px !important;
  color: #fff !important;
  font-weight: 800;
  text-transform: uppercase;
  text-decoration: none !important;
  text-align: center;
}
.element-tag { font-weight: bold; padding: 2px 8px; border-radius: 3px; text-transform: uppercase; font-size: 0.7rem; color: white; display: inline-flex; align-items: center; gap: 5px;}
.fire { background: #ff4500; }
.water { background: #1e90ff; }
.wind { background: #32cd32; color: #000; }
.earth { background: #8b4513; }
.neutral { background: #a9a9a9; color: #000; }
.poison { background: #006400; }
.holy { background: #ffd700; color: #000; }
.dark { background: #4b0082; }
.shadow { background: #4b0082; }
.ghost { background: #ee82ee; color: #000; }
.undead { background: #2f4f4f; }
.race-tag { background: #333; color: #eee; border: 1px solid #555; }
"""
    with open("docs/stylesheets/custom.css", "w", encoding="utf-8") as f: f.write(css_content)

# =========================
# 1. CORE LOGIC
# =========================

ELEMENT_ICONS = {
    "Neutral": ":material-circle-outline:", "Water": ":material-water:",
    "Earth": ":material-leaf:", "Fire": ":material-fire:",
    "Wind": ":material-weather-windy:", "Poison": ":material-flask-outline:",
    "Holy": ":material-white-balance-sunny:", "Dark": ":material-moon-waning-crescent:",
    "Shadow": ":material-moon-waning-crescent:", "Ghost": ":material-ghost:",
    "Undead": ":material-skull:"
}

def get_mapped_categories(raw_type, iid, usable_ids):
    # REGRA DE OURO: Se o ID está no item_db_usable, ele é CONSUMÍVEL
    if iid in usable_ids:
        return "Consumables", "CONSUMABLES"
    
    t = str(raw_type).strip().lower()
    if "hand" in t:
        name = t.replace("one-handed", "1H").replace("two-handed", "2H")
        if not name.endswith('s'): name += 's'
        return "Weapons", name.upper()
    
    weapon_list = ["bow", "dagger", "katar", "book", "knuckle", "whip", "staff", "mace", "axe", "sword"]
    for w in weapon_list:
        if w in t: return "Weapons", (w + "s").upper()
    
    armor_list = ["armor", "headgear", "shield", "garment", "cape", "shoes", "boots", "footgear"]
    for a in armor_list:
        if a in t: return "Armor", a.upper()

    return "Etc", "MISC"

def load_yaml(path):
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return yaml.safe_load(f)

def parse_lua(path):
    items = {}
    if not os.path.exists(path): return items
    with open(path, "r", encoding="latin-1", errors="ignore") as f:
        content = f.read()
    chunks = re.split(r'\[\s*(\d+)\s*\]\s*=\s*\{', content)
    for i in range(1, len(chunks), 2):
        item_id = int(chunks[i])
        block = chunks[i+1]
        name = re.search(r'NAME\s*=\s*["\'](.*?)["\']', block)
        display_name = name.group(1).strip() if name else f"Item {item_id}"
        desc_match = re.search(r'DESCRICAO\s*=\s*\{(.*?)\}', block, re.DOTALL)
        lines = []; found_type = "Etc"
        if desc_match:
            d_lines = re.findall(r'["\'](.*?)["\']', desc_match.group(1))
            for l in d_lines:
                cl = re.sub(r'\^[0-9a-fA-F]{6}', '', l).strip()
                if "Type:" in cl: found_type = cl.split("Type:")[-1].strip()
                if cl and "____" not in cl: lines.append(cl)
        items[item_id] = {"name": display_name, "desc": lines, "type": found_type}
    return items

# =========================
# 2. GENERATION
# =========================

def generate():
    if os.path.exists("docs"): shutil.rmtree("docs")
    generate_full_assets()
    
    lua_data = parse_lua("data/import_iteminfo.lua")
    aegis_to_id = {}
    usable_ids = set()

    # Mapear IDs Usáveis para correção de categoria
    db_files = {
        "equip": "data/item_db_equip.yml",
        "etc": "data/item_db_etc.yml",
        "usable": "data/item_db_usable.yml"
    }
    
    for key, path in db_files.items():
        d = load_yaml(path)
        if d and "Body" in d:
            for it in d["Body"]:
                if not it: continue
                iid = it["Id"]
                aegis_to_id[it["AegisName"].strip().lower()] = iid
                if key == "usable": usable_ids.add(iid)

    mob_db = load_yaml("data/mob_db.yml")
    item_drop_map = defaultdict(list)
    mobs = mob_db.get("Body", []) if mob_db else []
    
    for m in mobs:
        m_id, m_name = m.get('Id'), m.get('Name')
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            it_id = aegis_to_id.get(d["Item"].lower())
            if it_id:
                # Link para o monstro com profundidade corrigida
                link = f"| [{m_name}](../../../monsters/{m_id}.md) | {d['Rate']/100:.2f}% |"
                item_drop_map[it_id].append(link)

    tree = defaultdict(lambda: defaultdict(list))
    for iid, info in lua_data.items():
        m_cat, s_cat = get_mapped_categories(info["type"], iid, usable_ids)
        tree[m_cat][s_cat].append(iid)
        
        pg = [f"# {info['name']} (ID: {iid})", "", "### Description", "    " + "\n    ".join(info['desc']) if info['desc'] else "    *No description.*", "", "### Drop Table", "| Monster | Rate |", "| :--- | :--- |"]
        pg.extend(item_drop_map[iid] if item_drop_map[iid] else ["| - | Special Obtention |"])
        os.makedirs(f"docs/items/{m_cat}/{s_cat}", exist_ok=True)
        with open(f"docs/items/{m_cat}/{s_cat}/{iid}.md", "w", encoding="utf-8") as f: f.write("\n".join(pg))

    # Index Principal
    with open("docs/index.md", "w", encoding="utf-8") as f:
        f.write("# Tanelorn Wiki\n\n<div class='grid cards' markdown>\n- [Items Database](items/index.md)\n- [Monster Bestiary](monsters/index.md)\n</div>")

    # Indices de Itens
    items_idx = ["# Items Database", "\n<div class='grid cards' markdown>"]
    for mc in sorted(tree.keys()):
        items_idx.append(f"- [{mc}]({mc}/index.md)")
        sub_idx = [f"# {mc}", "\n<div class='grid cards' markdown>"]
        for sc in sorted(tree[mc].keys()):
            sub_idx.append(f"- [{sc}]({sc}/index.md)")
            list_pg = [f"# {sc}", "", "| ID | Name |", "| :--- | :--- |"]
            for iid in sorted(tree[mc][sc]):
                list_pg.append(f"| {iid} | [{lua_data[iid]['name']}]({iid}.md) |")
            with open(f"docs/items/{mc}/{sc}/index.md", "w", encoding="utf-8") as f: f.write("\n".join(list_pg))
        sub_idx.append("</div>")
        with open(f"docs/items/{mc}/index.md", "w", encoding="utf-8") as f: f.write("\n".join(sub_idx))
    items_idx.append("</div>")
    with open("docs/items/index.md", "w", encoding="utf-8") as f: f.write("\n".join(items_idx))

    # Bestiário de Monstros (Elite Design)
    m_idx = ["# Monster Bestiary", "", "| LVL | Element | Race | Size | Monster | ID |", "| :---: | :---: | :---: | :---: | :--- | :---: |"]
    for m in sorted(mobs, key=lambda x: (x.get('Level', 0), x['Id'])):
        el = m.get('Element', 'Neutral')
        ra = m.get('Race', 'Unknown')
        si = m.get('Size', 'Medium')
        tag_el = f'<span class="element-tag {el.lower()}">{ELEMENT_ICONS.get(el, "")} {el}</span>'
        tag_ra = f'<span class="element-tag race-tag">{ra}</span>'
        m_idx.append(f"| {m.get('Level', 0)} | {tag_el} | {tag_ra} | {si} | [{m['Name']}]({m['Id']}.md) | {m['Id']} |")
        
        m_pg = [f"# {m['Name']} (ID: {m['Id']})", "", f"**Stats**: LVL {m.get('Level')} | HP {m.get('Hp')} | Size {si}", f"**Type**: {tag_ra} | Element {tag_el}", "", "### Drops", "| Item | ID | Rate |", "| :--- | :--- | :--- |"]
        for d in (m.get("Drops", []) + m.get("MvpDrops", [])):
            it_id = aegis_to_id.get(d["Item"].lower())
            it_n = lua_data.get(it_id, {}).get('name', d['Item'])
            m_pg.append(f"| [{it_n}](../items/index.md) | {it_id} | {d['Rate']/100:.2f}% |")
        with open(f"docs/monsters/{m['Id']}.md", "w", encoding="utf-8") as f: f.write("\n".join(m_pg))
    with open(f"docs/monsters/index.md", "w", encoding="utf-8") as f: f.write("\n".join(m_idx))

if __name__ == "__main__":
    generate()
    print("--- WIKI GERADA COM SUCESSO ---")