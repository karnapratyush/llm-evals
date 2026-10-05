"""
Generate the schema text for the Text-to-SQL prompt from ipl_2026_relational.db,
including the table relationships read from the database's own foreign keys.

Outputs:
  schema.sql    - for the prompt: CREATE TABLE statements (with REFERENCES), a
                  relationship summary, and optional sample rows per table
  schema_er.md  - the same relationships as a Mermaid ER diagram (renders on GitHub / VS Code)

Everything is read from SQLite metadata (sqlite_master, pragma_table_info,
pragma_foreign_key_list), so it stays correct if generate_db_relational.py changes.

Run:  uv run python generate_schema.py
"""

import sqlite3

from config import DB_PATH, ER_DIAGRAM_PATH as ER_OUT, SCHEMA_PATH as SCHEMA_OUT

# ----- toggles -----
INCLUDE_SAMPLES = True   # False = DDL + relationships only (models must guess value formats)
N_SAMPLES = 3
# -------------------


def get_tables(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
    ).fetchall()]


def get_ddl(conn, table):
    return conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone()[0].strip()


def primary_key(conn, table):
    """Columns of the table's primary key, in key order."""
    cols = conn.execute(f"SELECT name, pk FROM pragma_table_info('{table}') WHERE pk > 0").fetchall()
    return [name for name, _ in sorted(cols, key=lambda c: c[1])]


def get_relationships(conn, tables):
    """One dict per foreign key: child.column -> parent.column plus its cardinality."""
    rels = []
    for child in tables:
        pk = primary_key(conn, child)
        fks = conn.execute(f'SELECT "from", "table", "to" FROM pragma_foreign_key_list(\'{child}\')').fetchall()
        fk_cols = {col for col, _, _ in fks}
        # a table whose whole primary key is made of foreign keys is a junction (many-to-many) table
        is_junction = len(pk) > 1 and set(pk) <= fk_cols
        for col, parent, parent_col in fks:
            if pk == [col]:
                kind = "one-to-one"          # the FK is also the child's whole PK
            elif is_junction:
                kind = "many-to-many (via junction)"
            else:
                kind = "many-to-one"
            rels.append(dict(child=child, col=col, parent=parent, parent_col=parent_col, kind=kind))
    return rels


def sample_rows(conn, table):
    cur = conn.execute(f"SELECT * FROM {table} LIMIT {N_SAMPLES}")
    header = [d[0] for d in cur.description]
    return header, cur.fetchall()


def write_schema(conn, tables, rels):
    with open(SCHEMA_OUT, "w", encoding="utf-8") as f:
        f.write("-- Schema for Text-to-SQL generation prompt\n")
        f.write(f"-- Source DB: {DB_PATH} (SQLite)\n\n")

        f.write("-- ========== RELATIONSHIPS (join paths) ==========\n")
        for r in rels:
            f.write(f"-- {r['child']}.{r['col']} -> {r['parent']}.{r['parent_col']}   ({r['kind']})\n")
        f.write("\n")

        for t in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            f.write(f"-- ========== {t} ({n} rows) ==========\n")
            f.write(get_ddl(conn, t) + ";\n")
            if INCLUDE_SAMPLES:
                header, rows = sample_rows(conn, t)
                f.write(f"-- sample rows:\n-- {' | '.join(header)}\n")
                for row in rows:
                    f.write("-- " + " | ".join("NULL" if v is None else str(v) for v in row) + "\n")
            f.write("\n")
    print(f"Saved schema ({len(tables)} tables, {len(rels)} relationships, samples={INCLUDE_SAMPLES}) -> {SCHEMA_OUT}")


def write_er_diagram(conn, tables, rels):
    """Mermaid erDiagram: parent ||--o{ child means one parent row, many child rows."""
    arrows = {"one-to-one": "||--o|", "many-to-one": "||--o{", "many-to-many (via junction)": "||--o{"}
    fk_cols = {(r["child"], r["col"]) for r in rels}
    lines = ["# IPL 2026 relational schema", "", "```mermaid", "erDiagram"]
    for r in rels:
        lines.append(f'    {r["parent"]} {arrows[r["kind"]]} {r["child"]} : "{r["col"]}"')
    for t in tables:
        pk = set(primary_key(conn, t))
        lines.append(f"    {t} {{")
        for name, ctype in conn.execute(f"SELECT name, type FROM pragma_table_info('{t}')").fetchall():
            keys = ",".join(k for k, on in [("PK", name in pk), ("FK", (t, name) in fk_cols)] if on)
            # Mermaid attribute names must be plain identifiers (no quotes, no leading digit)
            safe = name if name[0].isalpha() else f"c_{name}"
            lines.append(f"        {ctype or 'TEXT'} {safe} {keys}".rstrip())
        lines.append("    }")
    lines.append("```")
    with open(ER_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Saved ER diagram -> {ER_OUT}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    tables = get_tables(conn)
    rels = get_relationships(conn, tables)
    write_schema(conn, tables, rels)
    write_er_diagram(conn, tables, rels)
    conn.close()
