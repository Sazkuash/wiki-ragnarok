import yaml
import os
import shutil
from collections import defaultdict

# =========================
# UTILITÁRIOS
# =========================

def safe_folder(value, default="Other"):
    if not value:
        return default

    value = str(value).strip()

    aliases = {
        "petegg": "PetEgg",
        "pet_egg": "PetEgg",
        "pet egg": "PetEgg",
        "shadowgear": "Shadowgear",
        "shadow": "Shadowgear",
    }

    key = value.lower().replace("-", "").replace("_", "").replace(" ", "")
    return aliases.get(key, value)

def write_file(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# =========================
# GERADOR PRINCIPAL
# =========================

def generate():
    print("🔥 Gerando Wiki Ragnarok completa...")

    # -------------------------
    # CARREGAR DADOS
    # -------------------------
    with open("data/item_db_equip.yml", encoding="utf-8") as f:
        items = yaml.safe_load(f)["Body"]

    with open("data/mob_db.yml", encoding="utf-8") as f:
        mobs = yaml.safe_load(f)["Body"]

    # -------------------------
    # MAPEAR DROPS
    # -------------------------
    name_to_id = {i["AegisName"]: i["Id"] for i in items if i}
    drops_map = defaultdict(list)

    for m in mobs:
        if not m or "Drops" not in m:
            continue
        for d in m["Drops"]:
            item_id = name_to_id.get(d["Item"])
            if item_id:
                drops_map[item_id].append(
                    f"| {m['Name']} | {d['Rate']/100:.2f}% |"
                )

    # -------------------------
    # LIMPAR DOCS
    # -------------------------
    if os.path.exists("docs"):
        shutil.rmtree("docs")

    # -------------------------
    # HOME
    # -------------------------
    write_file("docs/index.md", [
        "# Ragnarok Wiki",
        "",
        "Bem-vindo à **Wiki de Itens do Ragnarok Online**."
    ])

    # -------------------------
    # AGRUPAR ITENS
    # -------------------------
    tree = defaultdict(lambda: defaultdict(list))

    for i in items:
        if not i:
            continue
        tipo = safe_folder(i.get("Type"), "Other")
        subtipo = safe_folder(i.get("SubType"), "General")
        tree[tipo][subtipo].append(i)

    # -------------------------
    # INDEX PRINCIPAL DE ITENS
    # -------------------------
    itens_index = [
        "# Database de Itens",
        "",
        "Escolha uma categoria:",
        ""
    ]

    for tipo in sorted(tree):
        itens_index.append(f"- **[{tipo}]({tipo}/index.md)**")

    write_file("docs/itens/index.md", itens_index)

    # -------------------------
    # GERAR CATEGORIAS
    # -------------------------
    for tipo, subtipos in tree.items():
        tipo_index = [
            f"# {tipo}",
            "",
            "Selecione uma subcategoria:",
            ""
        ]

        for subtipo in sorted(subtipos):
            tipo_index.append(f"- **[{subtipo}]({subtipo}/index.md)**")

        write_file(f"docs/itens/{tipo}/index.md", tipo_index)

        for subtipo, itens_lista in subtipos.items():
            subtipo_index = [
                f"# {subtipo}",
                "",
                "Itens disponíveis:",
                ""
            ]

            for i in sorted(itens_lista, key=lambda x: x["Id"]):
                subtipo_index.append(
                    f"- **[{i['Name']} ({i['Id']})]({i['Id']}.md)**"
                )

                drops = drops_map.get(i["Id"], ["| - | Não dropado |"])

                item_page = [
                    f"# {i['Name']} (ID: {i['Id']})",
                    "",
                    "## Atributos",
                    "",
                    "| Atributo | Valor |",
                    "|---------|------|",
                    f"| Ataque | {i.get('Attack', 0)} |",
                    f"| Slots | {i.get('Slots', 0)} |",
                    f"| Nível | {i.get('WeaponLevel', 0)} |",
                    "",
                    "## Drops",
                    "",
                    "| Monstro | Chance |",
                    "|--------|--------|",
                    *drops,
                    "",
                    "## Script",
                    "",
                    "```c",
                    str(i.get("Script", "N/A")),
                    "```"
                ]

                write_file(
                    f"docs/itens/{tipo}/{subtipo}/{i['Id']}.md",
                    item_page
                )

            write_file(
                f"docs/itens/{tipo}/{subtipo}/index.md",
                subtipo_index
            )

    print("✅ Wiki gerada com sucesso!")

# =========================
# EXECUÇÃO
# =========================

if __name__ == "__main__":
    generate()
