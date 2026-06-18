"""Notificacoes em tempo real do Game Skild.

Dois canais complementares:

1. SSE (Server-Sent Events): enquanto o painel do responsavel esta aberto, os
   alertas chegam na hora, sem recarregar a pagina.
2. Web Push: mesmo com o app fechado ou o celular bloqueado, o responsavel
   recebe a notificacao (requer PWA instalada e VAPID).

Tudo roda localmente, com dados simulados.
"""

from __future__ import annotations

import base64
import json
import queue
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VAPID_FILE = DATA_DIR / "vapid.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "push_subscriptions.json"

# Contato exigido pelo padrao VAPID (apenas identificacao do remetente).
VAPID_SUBJECT = "mailto:game-skild@example.com"


# ---------------------------------------------------------------------------
# Canal 1 — SSE (tempo real no app aberto)
# ---------------------------------------------------------------------------

class EventBroker:
    """Distribui eventos para todas as conexoes SSE abertas."""

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        listener: queue.Queue = queue.Queue(maxsize=20)
        with self._lock:
            self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener: queue.Queue) -> None:
        with self._lock:
            if listener in self._subscribers:
                self._subscribers.remove(listener)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        with self._lock:
            listeners = list(self._subscribers)
        for listener in listeners:
            try:
                listener.put_nowait(payload)
            except queue.Full:
                # Conexao lenta: descarta o evento para nao travar o servidor.
                pass


broker = EventBroker()


# ---------------------------------------------------------------------------
# Canal 2 — Web Push (VAPID)
# ---------------------------------------------------------------------------

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _generate_vapid_keys() -> dict[str, str]:
    """Cria um par de chaves VAPID (curva P-256) e devolve em base64url."""

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())

    private_raw = private_key.private_numbers().private_value.to_bytes(32, "big")
    public_point = private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )

    return {
        "private_key": _b64url(private_raw),
        "public_key": _b64url(public_point),
    }


def get_vapid_keys() -> dict[str, str]:
    """Carrega as chaves VAPID, gerando-as na primeira execucao."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if VAPID_FILE.exists():
        with VAPID_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    keys = _generate_vapid_keys()
    with VAPID_FILE.open("w", encoding="utf-8") as file:
        json.dump(keys, file, indent=2)
    return keys


def get_public_key() -> str:
    return get_vapid_keys()["public_key"]


def _load_subscriptions() -> list[dict[str, Any]]:
    if not SUBSCRIPTIONS_FILE.exists():
        return []
    with SUBSCRIPTIONS_FILE.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []


def _save_subscriptions(subscriptions: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SUBSCRIPTIONS_FILE.open("w", encoding="utf-8") as file:
        json.dump(subscriptions, file, ensure_ascii=False, indent=2)


def add_subscription(subscription: dict[str, Any]) -> int:
    """Guarda uma inscricao de push, evitando duplicatas pelo endpoint."""

    endpoint = subscription.get("endpoint")
    if not endpoint:
        raise ValueError("Inscricao de push sem endpoint.")

    subscriptions = _load_subscriptions()
    if not any(item.get("endpoint") == endpoint for item in subscriptions):
        subscriptions.append(subscription)
        _save_subscriptions(subscriptions)
    return len(subscriptions)


def send_web_push(title: str, body: str, extra: dict[str, Any] | None = None) -> dict[str, int]:
    """Envia uma notificacao push para todas as inscricoes registradas."""

    subscriptions = _load_subscriptions()
    if not subscriptions:
        return {"sent": 0, "failed": 0, "removed": 0}

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        # Biblioteca opcional ausente: o canal SSE continua funcionando.
        return {"sent": 0, "failed": 0, "removed": 0, "error": "pywebpush ausente"}

    keys = get_vapid_keys()
    payload = json.dumps(
        {"title": title, "body": body, **(extra or {})}, ensure_ascii=False
    )

    sent = 0
    still_valid: list[dict[str, Any]] = []
    removed = 0

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=keys["private_key"],
                vapid_claims={"sub": VAPID_SUBJECT},
            )
            sent += 1
            still_valid.append(subscription)
        except WebPushException as error:
            # 404/410 indicam inscricao expirada: removemos do arquivo.
            status = getattr(error.response, "status_code", None)
            if status in (404, 410):
                removed += 1
            else:
                still_valid.append(subscription)

    if removed:
        _save_subscriptions(still_valid)

    return {"sent": sent, "failed": len(subscriptions) - sent, "removed": removed}


def notify_alert(alert: dict[str, Any], message_record: dict[str, Any]) -> None:
    """Dispara os dois canais quando um alerta de risco e gerado."""

    level = alert.get("risk_level", "medio")
    sender = message_record.get("sender_name", "Jogador desconhecido")
    game = message_record.get("game", "jogo")
    score = alert.get("score", 0)

    title = f"Alerta de risco {level.upper()} no {game}"
    body = f"{sender} enviou uma mensagem suspeita (score {score}/100)."

    event_data = {
        "type": "alert",
        "risk_level": level,
        "score": score,
        "sender_name": sender,
        "game": game,
        "message": message_record.get("message", ""),
        "recommendation": alert.get("recommendation", ""),
    }

    # Canal 1: tempo real (app aberto).
    broker.publish("alert", event_data)

    # Canal 2: Web Push (app fechado). Nunca deixa o cadastro do alerta falhar.
    try:
        send_web_push(title, body, {"risk_level": level, "score": score})
    except Exception:
        pass
