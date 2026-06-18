"""API Flask do Game Skild.

O backend mantem dados simulados em JSON para facilitar apresentacoes e testes
academicos. Nenhum dado real de criancas deve ser inserido neste prototipo.

A analise combina duas camadas: regras explicaveis (analyzer) e um modelo de
aprendizado de maquina (classifier) que melhora com as correcoes humanas. Os
alertas sao enviados em tempo real por SSE e Web Push (notifications).
"""

from __future__ import annotations

import json
import os
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request, send_from_directory

import classifier
import notifications
from analyzer import analyze_message


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "database.json"
FRONTEND_DIR = BASE_DIR / "frontend"
DEFAULT_PORT = int(os.environ.get("PORT", "5000"))


app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


def now_iso() -> str:
    """Gera timestamp padronizado em UTC."""

    return datetime.now(timezone.utc).isoformat()


# Pontuacao minima atribuida quando o modelo eleva o risco acima das regras.
ML_LEVEL_FLOOR = {"baixo": 0, "medio": 35, "alto": 70}


def analyze_with_ml(
    message_text: str,
    *,
    sender_id: str | None = None,
    child_id: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combina as regras explicaveis com a previsao do modelo aprendido.

    O nivel final e o mais severo entre regra e modelo. Quando o aprendizado
    de maquina eleva o risco, registramos o motivo para manter a decisao
    transparente.
    """

    analysis = analyze_message(
        message_text, sender_id=sender_id, child_id=child_id, history=history
    )

    prediction = classifier.predict(message_text)
    analysis["ml"] = prediction

    rule_level = analysis["risk_level"]
    ml_level = prediction["level"]

    if classifier.LEVEL_ORDER[ml_level] > classifier.LEVEL_ORDER[rule_level]:
        analysis["risk_level"] = ml_level
        analysis["score"] = max(analysis["score"], ML_LEVEL_FLOOR[ml_level])
        analysis["recommendation"] = recommendation_for_level(ml_level)
        analysis["should_block"] = ml_level == "alto"
        analysis["risk_source"] = "aprendizado_de_maquina"
        for term in prediction.get("influential_terms", []):
            if term not in analysis["matched_terms"]:
                analysis["matched_terms"].append(term)
    else:
        analysis["risk_source"] = "regras"

    return analysis


def recommendation_for_level(level: str) -> str:
    """Recomendacao humana proporcional ao nivel (espelha o analyzer)."""

    from analyzer import recommendation_for

    return recommendation_for(level)


def get_lan_ips() -> list[str]:
    """Retorna possiveis IPs da rede local para acesso pelo celular."""

    ips: set[str] = set()

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass

    # Este metodo descobre o IP usado na rede sem enviar dados reais.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass

    return sorted(ips)


def empty_database() -> dict[str, list[dict[str, Any]]]:
    """Estrutura inicial do armazenamento local."""

    return {"children": [], "messages": [], "alerts": []}


def load_database() -> dict[str, list[dict[str, Any]]]:
    """Carrega o JSON local; cria arquivo vazio se ele ainda nao existir."""

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        save_database(empty_database())
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_database(data: dict[str, list[dict[str, Any]]]) -> None:
    """Persiste os dados simulados em disco."""

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def create_alert(message_record: dict[str, Any]) -> dict[str, Any] | None:
    """Cria alerta quando a analise indicar risco medio ou alto."""

    analysis = message_record["analysis"]
    if analysis["risk_level"] == "baixo":
        return None

    return {
        "id": str(uuid.uuid4()),
        "message_id": message_record["id"],
        "child_id": message_record["child_id"],
        "sender_id": message_record["sender_id"],
        "risk_level": analysis["risk_level"],
        "score": analysis["score"],
        "status": "novo",
        "created_at": now_iso(),
        "recommendation": analysis["recommendation"],
    }


@app.after_request
def add_cors_headers(response):
    """Permite que a interface estatica acesse a API no ambiente local."""

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/")
def index():
    """Entrega a interface dos responsaveis."""

    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/health")
def health():
    """Endpoint simples para verificar se o backend esta ativo."""

    return jsonify({"status": "ok", "app": "Game Skild"})


@app.route("/api/network")
def network():
    """Mostra URLs uteis para abrir o prototipo no computador e no celular."""

    forwarded_host = request.headers.get("X-Forwarded-Host")
    current_host = forwarded_host or request.host
    port = current_host.rsplit(":", 1)[-1] if ":" in current_host else str(DEFAULT_PORT)
    lan_urls = [f"http://{ip}:{port}" for ip in get_lan_ips()]

    return jsonify(
        {
            "current_url": request.host_url.rstrip("/"),
            "lan_urls": lan_urls,
            "port": port,
            "note": "Use um destes links no celular conectado ao mesmo Wi-Fi.",
        }
    )


@app.route("/api/children", methods=["GET", "POST", "OPTIONS"])
def children():
    """Lista ou cadastra criancas ficticias do prototipo."""

    if request.method == "OPTIONS":
        return "", 204

    data = load_database()

    if request.method == "GET":
        return jsonify(data["children"])

    payload = request.get_json(force=True, silent=True) or {}
    child_name = (payload.get("child_name") or "").strip()
    responsible_name = (payload.get("responsible_name") or "").strip()
    age = payload.get("age")

    if not child_name or not responsible_name:
        return jsonify({"error": "Informe nome da crianca e responsavel."}), 400

    child = {
        "id": str(uuid.uuid4()),
        "child_name": child_name,
        "responsible_name": responsible_name,
        "age": age,
        "created_at": now_iso(),
        "notice": "Cadastro ficticio para prototipo academico.",
    }

    data["children"].append(child)
    save_database(data)
    return jsonify(child), 201


@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze_only():
    """Analisa uma mensagem sem gravar no historico."""

    if request.method == "OPTIONS":
        return "", 204

    payload = request.get_json(force=True, silent=True) or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Informe a mensagem a ser analisada."}), 400

    return jsonify({"analysis": analyze_with_ml(message)})


@app.route("/api/messages", methods=["GET", "POST", "OPTIONS"])
def messages():
    """Lista mensagens ou registra uma nova conversa simulada."""

    if request.method == "OPTIONS":
        return "", 204

    data = load_database()

    if request.method == "GET":
        return jsonify(data["messages"])

    payload = request.get_json(force=True, silent=True) or {}
    message_text = (payload.get("message") or "").strip()
    child_id = (payload.get("child_id") or "").strip()
    sender_name = (payload.get("sender_name") or "Jogador desconhecido").strip()
    sender_id = (payload.get("sender_id") or sender_name.lower().replace(" ", "-")).strip()
    sender_type = (payload.get("sender_type") or "desconhecido").strip()
    game = (payload.get("game") or "Jogo simulado").strip()

    if not child_id or not message_text:
        return jsonify({"error": "Informe crianca e mensagem."}), 400

    child_exists = any(child["id"] == child_id for child in data["children"])
    if not child_exists:
        return jsonify({"error": "Crianca nao encontrada no cadastro simulado."}), 404

    analysis = analyze_with_ml(
        message_text,
        sender_id=sender_id,
        child_id=child_id,
        history=data["messages"],
    )

    message_record = {
        "id": str(uuid.uuid4()),
        "child_id": child_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_type": sender_type,
        "game": game,
        "message": message_text,
        "created_at": now_iso(),
        "analysis": analysis,
    }

    alert = create_alert(message_record)
    data["messages"].append(message_record)
    if alert:
        data["alerts"].append(alert)
        notifications.notify_alert(alert, message_record)
    save_database(data)

    return jsonify({"message": message_record, "alert": alert}), 201


@app.route("/api/alerts")
def alerts():
    """Retorna alertas com dados basicos da mensagem relacionada."""

    data = load_database()
    messages_by_id = {item["id"]: item for item in data["messages"]}
    children_by_id = {item["id"]: item for item in data["children"]}

    enriched_alerts = []
    for alert in data["alerts"]:
        message = messages_by_id.get(alert["message_id"], {})
        child = children_by_id.get(alert["child_id"], {})
        enriched_alerts.append(
            {
                **alert,
                "child_name": child.get("child_name", "Crianca simulada"),
                "sender_name": message.get("sender_name", "Jogador desconhecido"),
                "game": message.get("game", "Jogo simulado"),
                "message": message.get("message", ""),
                "matches": message.get("analysis", {}).get("matches", []),
                "matched_terms": message.get("analysis", {}).get("matched_terms", []),
                "should_block": message.get("analysis", {}).get("should_block", False),
            }
        )

    return jsonify(enriched_alerts)


@app.route("/api/seed", methods=["POST"])
def seed():
    """Popula a aplicacao com mensagens ficticias para demonstracao."""

    child_id = str(uuid.uuid4())
    database = {
        "children": [
            {
                "id": child_id,
                "child_name": "Crianca Simulada",
                "responsible_name": "Responsavel Simulado",
                "age": 11,
                "created_at": now_iso(),
                "notice": "Cadastro ficticio para prototipo academico.",
            }
        ],
        "messages": [],
        "alerts": [],
    }

    examples = [
        {
            "sender_id": "player-legal",
            "sender_name": "PlayerLegal",
            "sender_type": "jogador",
            "game": "Arena Escolar",
            "message": "Boa partida, vamos defender a base juntos.",
        },
        {
            "sender_id": "contato-fora",
            "sender_name": "ContatoFora",
            "sender_type": "desconhecido",
            "game": "Arena Escolar",
            "message": "Me chama no WhatsApp depois do jogo.",
        },
        {
            "sender_id": "presenteiro",
            "sender_name": "Presenteiro",
            "sender_type": "desconhecido",
            "game": "Mundo dos Blocos",
            "message": "Te dou uma skin se voce passar seu contato.",
        },
        {
            "sender_id": "segredo",
            "sender_name": "Segredo",
            "sender_type": "desconhecido",
            "game": "Mundo dos Blocos",
            "message": "Nao conta para seus pais, e segredo. Apaga a conversa.",
        },
    ]

    for example in examples:
        analysis = analyze_with_ml(
            example["message"],
            sender_id=example["sender_id"],
            child_id=child_id,
            history=database["messages"],
        )
        record = {
            "id": str(uuid.uuid4()),
            "child_id": child_id,
            "created_at": now_iso(),
            "analysis": analysis,
            **example,
        }
        alert = create_alert(record)
        database["messages"].append(record)
        if alert:
            database["alerts"].append(alert)

    save_database(database)
    return jsonify({"status": "seeded", "children": 1, "messages": len(examples)})


@app.route("/api/feedback", methods=["POST", "OPTIONS"])
def feedback():
    """Recebe a correcao humana de um alerta e re-treina o modelo.

    E aqui que o sistema "aprende com o que acontece": quando um responsavel
    confirma ou corrige o nivel de risco, o exemplo entra na base de
    aprendizado e o modelo melhora imediatamente.
    """

    if request.method == "OPTIONS":
        return "", 204

    payload = request.get_json(force=True, silent=True) or {}
    message_text = (payload.get("message") or "").strip()
    level = (payload.get("level") or "").strip()

    if not message_text or not level:
        return jsonify({"error": "Informe a mensagem e o nivel correto."}), 400

    try:
        stats = classifier.add_feedback(message_text, level, source="responsavel")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"status": "aprendido", "model": stats}), 201


@app.route("/api/model")
def model_status():
    """Mostra o estado atual do modelo de aprendizado de maquina."""

    return jsonify(classifier.train())


@app.route("/api/stream")
def stream():
    """Canal SSE: envia alertas em tempo real enquanto o painel esta aberto."""

    def event_generator():
        listener = notifications.broker.subscribe()
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                yield listener.get()
        except GeneratorExit:
            pass
        finally:
            notifications.broker.unsubscribe(listener)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return Response(event_generator(), headers=headers)


@app.route("/api/push/public-key")
def push_public_key():
    """Devolve a chave publica VAPID usada para inscrever o navegador."""

    return jsonify({"public_key": notifications.get_public_key()})


@app.route("/api/push/subscribe", methods=["POST", "OPTIONS"])
def push_subscribe():
    """Registra a inscricao de Web Push do responsavel."""

    if request.method == "OPTIONS":
        return "", 204

    subscription = request.get_json(force=True, silent=True) or {}
    try:
        total = notifications.add_subscription(subscription)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"status": "inscrito", "subscriptions": total}), 201


@app.route("/api/push/test", methods=["POST"])
def push_test():
    """Dispara uma notificacao de teste para validar o Web Push."""

    result = notifications.send_web_push(
        "Game Skild", "Notificacoes ativadas com sucesso.", {"test": True}
    )
    return jsonify(result)


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = DEFAULT_PORT
    debug = os.environ.get("FLASK_DEBUG") == "1"

    print("Game Skild iniciado.")
    print(f"Computador: http://127.0.0.1:{port}")
    for ip in get_lan_ips():
        print(f"Celular na mesma Wi-Fi: http://{ip}:{port}")

    # threaded=True garante que o SSE nao bloqueie as demais requisicoes.
    app.run(debug=debug, host=host, port=port, threaded=True)
