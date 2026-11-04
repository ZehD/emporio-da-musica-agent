"""The agent's tools: plain functions with fixed parameters.

The model decides which tool to call. The code decides what comes back,
does every calculation (spec B5) and enforces the identity check on
orders (spec B12). The model never queries the data directly.
"""

import difflib
import json
import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path

from .clock import now, today
from .data import Store

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT / "docs" / "policies"
HANDOFF_DIR = ROOT / "handoffs"

POLICY_SECTIONS = {
    "sobre_a_loja": "01_sobre_a_loja.md",
    "horario_de_funcionamento": "02_horario_de_funcionamento.md",
    "formas_de_pagamento": "03_formas_de_pagamento.md",
    "trocas_e_devolucoes": "04_trocas_e_devolucoes.md",
    "frete_e_entregas": "05_frete_e_entregas.md",
    "promocoes_e_descontos": "06_promocoes_e_descontos.md",
    "atendimento": "07_atendimento.md",
    "garantia": "08_garantia.md",
    "privacidade": "09_privacidade.md",
}

ORDER_STATUS = {
    "pending": "aguardando confirmação de pagamento",
    "confirmed": "pagamento confirmado, em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}

PIX_DISCOUNT = 0.05
# Installment rules from manual §3.1: (max installments, minimum installment value).
INSTALLMENT_TIERS = [(3, 50.0), (6, 80.0), (12, 100.0)]
CATEGORY_WORDS = {
    "violao": "Violões", "violoes": "Violões",
    "guitarra": "Guitarras", "guitarras": "Guitarras",
    "baixo": "Baixos", "baixos": "Baixos",
    "bateria": "Baterias e Percussão", "baterias": "Baterias e Percussão",
    "teclado": "Teclados e Pianos", "teclados": "Teclados e Pianos",
    "piano": "Teclados e Pianos", "pianos": "Teclados e Pianos",
    "ukulele": "Ukuleles", "ukuleles": "Ukuleles",
}
STOPWORDS = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma",
             "para", "com", "em", "no", "na", "que", "tem", "ate", "r", "reais", "bom", "boa"}


# ---------- helpers ----------

def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _norm(text)) if t not in STOPWORDS and len(t) > 1]


def _money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def max_installments(amount: float) -> int:
    best = 1
    for max_n, min_value in INSTALLMENT_TIERS:
        for n in range(1, max_n + 1):
            if amount / n >= min_value:
                best = max(best, n)
    return best


def _availability(row) -> str:
    if row["status"] == "discontinued":
        return "descontinuado (não é mais vendido)"
    if row["status"] == "coming_soon":
        return "em breve (ainda não disponível para venda)"
    if row["stock_quantity"] <= 0:
        return "esgotado no momento"
    return "disponível"


def _is_sellable(row) -> bool:
    return row["status"] == "active" and row["stock_quantity"] > 0


def _pricing(row) -> dict:
    """All price math in one place (manual §3, §3.1, §6.2)."""
    price = float(row["price_brl"])
    promo = row.get("promo_percent")
    has_promo = promo == promo and promo is not None  # NaN check
    final = round(price * (1 - promo / 100), 2) if has_promo else price
    pricing = {
        "preco_tabela": _money(price),
        "preco_final": _money(final),
        "parcelamento": f"até {max_installments(final)}x sem juros de "
                        f"{_money(final / max_installments(final))}",
    }
    if has_promo:
        pricing["promocao_ativa"] = f"{row['promo_name']}: {promo:g}% de desconto"
        pricing["pix"] = "desconto PIX de 5% não se aplica (preço já promocional)"
    else:
        pricing["promocao_ativa"] = None
        pricing["pix"] = f"{_money(round(price * (1 - PIX_DISCOUNT), 2))} à vista no PIX (5% off)"
    return pricing


def _final_price(row) -> float:
    promo = row.get("promo_percent")
    if promo == promo and promo is not None:
        return round(float(row["price_brl"]) * (1 - promo / 100), 2)
    return float(row["price_brl"])


def _summary(row) -> dict:
    return {
        "id": int(row["product_id"]),
        "nome": row["name"],
        "categoria": row["category"],
        "disponibilidade": _availability(row),
        "estoque": int(row["stock_quantity"]),
        **_pricing(row),
    }


# ---------- tools ----------

def search_products(store: Store, query: str = "", category: str = "",
                    max_price: float | None = None, in_stock_only: bool = True) -> dict:
    df = store.products
    # "violão" in free text means the category, not any description that mentions it.
    words = _tokens(query)
    if not category:
        for w in words:
            if w in CATEGORY_WORDS:
                category = CATEGORY_WORDS[w]
                words = [x for x in words if x != w]
                break
    if category:
        df = df[df["category"].map(_norm) == _norm(category)]
    if in_stock_only:
        df = df[df.apply(_is_sellable, axis=1)]
    if max_price is not None:
        df = df[df.apply(_final_price, axis=1) <= max_price]

    if words:
        haystack = df.apply(
            lambda r: _norm(f"{r['name']} {r['description']} {r['specs']} {r['category']}"), axis=1
        )
        scores = haystack.map(lambda h: sum(w in h for w in words))
        df = df[scores > 0].assign(_score=scores[scores > 0])
        df = df.sort_values(["_score", "price_brl"], ascending=[False, True])
    else:
        df = df.sort_values("price_brl")

    results = [_summary(r) for _, r in df.head(10).iterrows()]
    out = {"total_encontrado": int(len(df)), "produtos": results}
    if not results:
        out["observacao"] = "Nenhum produto encontrado com esses critérios no catálogo atual."
    return out


def get_product(store: Store, name_or_id: str) -> dict:
    df = store.products
    key = str(name_or_id).strip()
    match = df[df["product_id"] == int(key)] if key.isdigit() else df.iloc[0:0]

    if match.empty:
        wanted = set(_tokens(key))
        overlap = df["name"].map(lambda n: len(wanted & set(_tokens(n))) / max(len(wanted), 1))
        best = overlap.max()
        if best >= 0.6:
            match = df[overlap == best]

    if match.empty:
        close = difflib.get_close_matches(_norm(key), df["name"].map(_norm).tolist(), n=3, cutoff=0.4)
        names = df[df["name"].map(_norm).isin(close)]["name"].tolist()
        return {"encontrado": False, "observacao": "Produto não encontrado no catálogo.",
                "sugestoes_parecidas": names}

    products = []
    for _, row in match.head(3).iterrows():
        products.append({
            **_summary(row),
            "descricao": row["description"],
            "especificacoes": json.loads(row["specs"]) if row["specs"] else {},
        })
    return {"encontrado": True, "produtos": products}


def get_order(store: Store, order_id: str, email_or_phone: str) -> dict:
    refusal = {"autorizado": False,
               "observacao": "Não foi possível confirmar o pedido com esses dados. "
                             "Peça ao cliente para conferir o número do pedido e o e-mail ou telefone do cadastro."}
    if not str(order_id).strip().isdigit():
        return refusal
    orders = store.orders[store.orders["order_id"] == int(order_id)]
    if orders.empty:
        return refusal
    order = orders.iloc[0]
    customer = store.customers[store.customers["customer_id"] == order["customer_id"]].iloc[0]

    # Identity check (spec B12): order number + email or phone on file.
    given = str(email_or_phone).strip()
    digits = re.sub(r"\D", "", given)
    email_ok = "@" in given and _norm(given) == _norm(customer["email"])
    phone_ok = len(digits) >= 8 and re.sub(r"\D", "", customer["phone"]).endswith(digits[-8:])
    if not (email_ok or phone_ok):
        return refusal

    items = store.order_items[store.order_items["order_id"] == order["order_id"]]
    names = store.products.set_index("product_id")["name"]
    result = {
        "autorizado": True,
        "pedido": int(order["order_id"]),
        "cliente_primeiro_nome": customer["name"].split()[0],
        "cidade": customer["city"],
        "status": ORDER_STATUS.get(order["status"], order["status"]),
        "data_pedido": order["order_date"],
        "itens": [f"{r['quantity']}x {names.get(r['product_id'], 'produto')}" for _, r in items.iterrows()],
        "total": _money(order["total_brl"]),
        "pagamento": order["payment_method"],
        "codigo_rastreamento": order["tracking_code"] or None,
        "previsao_entrega": order["estimated_delivery"] or None,
        "observacoes": order["notes"] or None,
        "hoje": today().isoformat(),
    }
    # Date math for return/exchange questions is done here, not by the model.
    order_day = date.fromisoformat(order["order_date"])
    result["dias_desde_o_pedido"] = (today() - order_day).days
    if order["estimated_delivery"]:
        delivered = date.fromisoformat(order["estimated_delivery"])
        result["dias_desde_a_entrega_prevista"] = (today() - delivered).days
    return result


def get_policy(store: Store, section: str) -> dict:
    filename = POLICY_SECTIONS.get(section)
    if not filename:
        return {"erro": f"Seção desconhecida. Opções: {', '.join(POLICY_SECTIONS)}"}
    return {"secao": section, "texto": (POLICY_DIR / filename).read_text(encoding="utf-8")}


def handoff_to_human(store: Store, reason: str, summary: str) -> dict:
    HANDOFF_DIR.mkdir(exist_ok=True)
    ticket = f"EM-{uuid.uuid4().hex[:6].upper()}"
    payload = {"ticket": ticket, "created_at": now().isoformat(timespec="minutes"),
               "reason": reason, "summary": summary}
    (HANDOFF_DIR / f"{ticket}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"ticket": ticket, "prazo_retorno": "até 24 horas úteis"}


TOOLS = {
    "search_products": search_products,
    "get_product": get_product,
    "get_order": get_order,
    "get_policy": get_policy,
    "handoff_to_human": handoff_to_human,
}


def schemas(store: Store) -> list[dict]:
    """JSON schemas the model sees. Descriptions say *when* to use each tool."""
    categories = store.categories["name"].tolist()
    return [
        {"type": "function", "function": {
            "name": "search_products",
            "description": "Busca produtos no catálogo por tipo, característica, categoria ou faixa de preço. "
                           "Use para recomendações, listas de opções e alternativas a produtos indisponíveis.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Palavras-chave (ex.: 'nylon iniciante', 'elétrico', 'Yamaha')."},
                "category": {"type": "string", "enum": categories},
                "max_price": {"type": "number", "description": "Preço máximo em reais, já considerando promoções."},
                "in_stock_only": {"type": "boolean", "description": "Padrão true. Use false só para checar se um item existe mas está indisponível."},
            }},
        }},
        {"type": "function", "function": {
            "name": "get_product",
            "description": "Detalhes de um produto específico: preço, promoção ativa, PIX, parcelamento, estoque e especificações. "
                           "Use sempre antes de informar preço ou disponibilidade de um produto.",
            "parameters": {"type": "object", "properties": {
                "name_or_id": {"type": "string", "description": "Nome do produto (pode ser parcial) ou ID."},
            }, "required": ["name_or_id"]},
        }},
        {"type": "function", "function": {
            "name": "get_order",
            "description": "Status de um pedido. Exige o número do pedido E o e-mail ou telefone do cadastro. "
                           "Se o cliente não informou os dois, peça antes de chamar.",
            "parameters": {"type": "object", "properties": {
                "order_id": {"type": "string"},
                "email_or_phone": {"type": "string"},
            }, "required": ["order_id", "email_or_phone"]},
        }},
        {"type": "function", "function": {
            "name": "get_policy",
            "description": "Texto integral de uma seção do manual da loja. Use para regras: trocas, devoluções, "
                           "garantia, frete, formas de pagamento, parcelamento, promoções, privacidade.",
            "parameters": {"type": "object", "properties": {
                "section": {"type": "string", "enum": list(POLICY_SECTIONS)},
            }, "required": ["section"]},
        }},
        {"type": "function", "function": {
            "name": "handoff_to_human",
            "description": "Encaminha o atendimento para a equipe: reclamações, pedidos de devolução/troca a processar, "
                           "casos que o manual não cobre ou quando o cliente pede um humano.",
            "parameters": {"type": "object", "properties": {
                "reason": {"type": "string", "enum": ["reclamacao", "devolucao_ou_troca", "caso_nao_coberto", "pedido_do_cliente"]},
                "summary": {"type": "string", "description": "Resumo do caso para a equipe, com nº do pedido se houver."},
            }, "required": ["reason", "summary"]},
        }},
    ]
