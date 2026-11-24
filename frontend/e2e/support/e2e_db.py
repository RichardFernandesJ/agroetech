"""Utilitário do E2E: mexe direto no SQLite descartável da API de teste.

Uso: python e2e/support/e2e_db.py <comando> [argumentos]

- boost <xp> <agc>      define o XP e o saldo do jogador mais recente
- give <item> <qtd>     adiciona itens à fazenda mais recente
- rewind <horas>        volta o relógio dos animais (simula tempo offline)
- finish                faz os trabalhos de fabricação em aberto terminarem agora
"""

import sqlite3
import sys
import uuid
from datetime import UTC, datetime

DB = "../backend/e2e.sqlite3"


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def latest_owner(connection: sqlite3.Connection) -> str:
    """Dono da fazenda mais recente: o jogador do teste em andamento."""
    (owner,) = connection.execute(
        "select owner_id from properties order by created_at desc limit 1"
    ).fetchone()
    return owner


def main() -> None:
    command, args = sys.argv[1], sys.argv[2:]
    connection = sqlite3.connect(DB)
    if command == "boost":
        owner = latest_owner(connection)
        connection.execute("update player_progress set xp=? where user_id=?", (int(args[0]), owner))
        connection.execute("update wallets set balance=? where user_id=?", (int(args[1]), owner))
    elif command == "give":
        item, quantity = args[0], int(args[1])
        (property_id,) = connection.execute(
            "select id from properties order by created_at desc limit 1"
        ).fetchone()
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
    elif command == "finish":
        connection.execute(
            "update production_jobs set finish_at=strftime('%Y-%m-%d %H:%M:%f', 'now', '-1 seconds')"
            " where collected_at is null"
        )
    else:
        raise SystemExit(f"comando desconhecido: {command}")
    connection.commit()
    connection.close()


if __name__ == "__main__":
    main()
