#!/usr/bin/env python3
"""Roteiro de fumaça da API: percorre o ciclo principal contra um servidor em execução.

Uso (stack do Docker Compose em http://localhost:8000):

    python scripts/smoke.py
    python scripts/smoke.py http://localhost:8000 --skip-concurrency

Só usa a biblioteca padrão. Cria um jogador novo a cada execução (nome aleatório) e
termina com código 0 (tudo certo) ou 1 (alguma verificação falhou).

O passo de concorrência dispara compras simultâneas com saldo para apenas uma: com
PostgreSQL e as travas de linha, exatamente uma pode dar certo e o saldo nunca fica
negativo. Em SQLite use --skip-concurrency (o arquivo único não reproduz essa disputa).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib import error, request

PASSED: list[str] = []
FAILED: list[str] = []


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.token: str | None = None

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict | list | None]:
        data = json.dumps(body).encode() if body is not None else None
        req = request.Request(f"{self.base}{path}", data=data, method=method)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with request.urlopen(req, timeout=30) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return exc.code, {"detail": raw.decode(errors="replace")}


def check(name: str, condition: bool, detail: object = "") -> None:
    (PASSED if condition else FAILED).append(name)
    print(f"  {'OK  ' if condition else 'FALHA'} {name}" + ("" if condition else f"  -> {detail}"))


def run(base: str, skip_concurrency: bool) -> None:
    api = Api(base)
    print(f"Agro & Tech — roteiro de fumaça em {api.base}")

    status, body = api.call("GET", "/health")
    check("saúde da API", status == 200, (status, body))

    suffix = uuid.uuid4().hex[:8]
    credentials = {
        "email": f"smoke_{suffix}@example.com",
        "username": f"smoke_{suffix}",
        "password": "senha-forte-123",
    }
    status, _ = api.call("POST", "/api/v1/auth/register", credentials)
    check("cadastro", status == 201, status)
    status, body = api.call(
        "POST", "/api/v1/auth/login", {"login": credentials["email"], "password": credentials["password"]}
    )
    check("login", status == 200 and bool(body and body.get("access_token")), (status, body))
    if status != 200 or not body:
        return
    api.token = body["access_token"]

    status, body = api.call("POST", "/api/v1/characters", {"name": "Fumaca Teste"})
    check("perfil e fazenda inicial", status == 201, (status, body))
    status, farms = api.call("GET", "/api/v1/properties")
    check("fazenda listada (6 talhões)", status == 200 and farms[0]["plot_count"] == 6, (status, farms))
    if status != 200 or not farms:
        return
    prop = farms[0]["id"]
    base_prop = f"/api/v1/properties/{prop}"

    status, _ = api.call("POST", "/api/v1/properties", {"name": "Outra", "area_hectares": 3})
    check("segunda fazenda recusada (409)", status == 409, status)

    status, body = api.call("POST", f"{base_prop}/plantings", {"crop_id": "milho", "plot_index": 0})
    check("plantio", status == 201, (status, body))
    status, body = api.call("GET", "/api/v1/progress")
    check("XP do plantio", status == 200 and body["xp"] == 2, (status, body))

    status, body = api.call("GET", "/api/v1/wallet")
    check("saldo inicial de 100 AGC", status == 200 and body["balance"] == 100, (status, body))

    key = {"Idempotency-Key": f"fumaca-{suffix}"}
    buy = {"item_id": "seed_milho", "quantity": 1}
    s1, b1 = api.call("POST", f"{base_prop}/market/buy", buy, key)
    s2, b2 = api.call("POST", f"{base_prop}/market/buy", buy, key)
    check(
        "compra idempotente (cobra uma vez)",
        s1 == s2 == 200 and b1["balance"] == b2["balance"] == 92 and b2["replayed"] is True,
        (s1, s2, b1, b2),
    )

    for name, path in [
        ("estado das construções", f"{base_prop}/buildings"),
        ("estado dos animais", f"{base_prop}/animals"),
        ("estado da fabricação", f"{base_prop}/crafting"),
        ("talentos", "/api/v1/talents"),
        ("catálogo de talentos", "/api/v1/catalog/talents"),
        ("ofertas do mercado", "/api/v1/market/offers"),
        ("praça: regras e cotações", "/api/v1/exchange/info"),
        ("praça: anúncios", "/api/v1/exchange/listings"),
        ("trocas: regras", "/api/v1/trades/info"),
        ("trocas: propostas", "/api/v1/trades"),
    ]:
        status, body = api.call("GET", path)
        check(name, status == 200, (status, body))

    if not skip_concurrency:
        # Saldo 92: cada café custa 90; só uma das compras simultâneas pode passar.
        def buy_coffee(_: int) -> int:
            return api.call(
                "POST",
                f"{base_prop}/market/buy",
                {"item_id": "seed_cafe", "quantity": 1},
                {"Idempotency-Key": f"cafe-{uuid.uuid4().hex}"},
            )[0]

        with ThreadPoolExecutor(max_workers=10) as pool:
            codes = list(pool.map(buy_coffee, range(10)))
        check("compras simultâneas: exatamente uma passa", codes.count(200) == 1, codes)
        check("compras simultâneas: sem erro 500", 500 not in codes, codes)
        status, wallet = api.call("GET", "/api/v1/wallet")
        check("saldo nunca negativo (2 AGC)", wallet["balance"] == 2, wallet)

    status, ledger = api.call("GET", "/api/v1/wallet/ledger?limit=100")
    status_w, wallet = api.call("GET", "/api/v1/wallet")
    total = sum(entry["amount"] for entry in ledger["entries"]) if status == 200 else None
    check("extrato concilia com o saldo", status == status_w == 200 and total == wallet["balance"], (total, wallet))


def main() -> int:
    # O console do Windows costuma usar uma codificação que estraga os acentos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("base", nargs="?", default="http://localhost:8000", help="URL base da API")
    parser.add_argument("--skip-concurrency", action="store_true", help="pula o passo de compras simultâneas")
    args = parser.parse_args()
    try:
        run(args.base, args.skip_concurrency)
    except error.URLError as exc:
        print(f"Não foi possível conectar a {args.base}: {exc.reason}")
        return 1
    print(f"\n{len(PASSED)} verificações ok, {len(FAILED)} com falha.")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
