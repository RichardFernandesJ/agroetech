"""Utilitário do E2E: mexe direto no SQLite descartável da API de teste.

Uso: python e2e/support/e2e_db.py <comando> [argumentos]

- boost <xp> <agc>      define o XP do jogador e o saldo da carteira
- give <item> <qtd>     adiciona itens ao inventário da fazenda
- rewind <horas>        volta o relógio dos animais (simula tempo offline)
"""

import sqlite3
import sys
import uuid
from datetime import UTC, datetime

DB = "../backend/e2e.sqlite3"


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def main() -> None:
    command, args = sys.argv[1], sys.argv[2:]
    connection = sqlite3.connect(DB)
    if command == "boost":
        connection.execute("update player_progress set xp=?", (int(args[0]),))
        connection.execute("update wallets set balance=?", (int(args[1]),))
    elif command == "give":
        item, quantity = args[0], int(args[1])
        (property_id,) = connection.execute("select id from properties limit 1").fetchone()
        row = connection.execute(
            "select id from inventory_items where property_id=? and item_id=?", (property_id, item)
        ).fetchone()
        if row:
            connection.execute(
                "update inventory_items set quantity=quantity+? where id=?", (quantity, row[0])
            )
        else:
            connection.execute(
                "insert into inventory_items (id, property_id, item_id, quantity, created_at, updated_at) "
                "values (?,?,?,?,?,?)",
                (uuid.uuid4().hex, property_id, item, quantity, now(), now()),
            )
    elif command == "rewind":
        modifier = f"-{int(float(args[0]) * 3600)} seconds"
        connection.execute(
            "update animals set last_sync_at=strftime('%Y-%m-%d %H:%M:%f', last_sync_at, ?),"
            " fed_until=strftime('%Y-%m-%d %H:%M:%f', fed_until, ?) where fed_until is not null",
            (modifier, modifier),
        )
        connection.execute(
            "update animals set last_sync_at=strftime('%Y-%m-%d %H:%M:%f', last_sync_at, ?)"
            " where fed_until is null",
            (modifier,),
        )
    else:
        raise SystemExit(f"comando desconhecido: {command}")
    connection.commit()
    connection.close()


if __name__ == "__main__":
    main()
