"""Avaliacao do classificador de risco do Guardiao Gamer.

Roda o classificador de regras sobre a base rotulada simulada
(`data/simulated_messages.json`) e reporta metricas de desempenho:
matriz de confusao, acuracia, precisao, revocacao (recall) e F1 por classe.

Uso:
    cd backend
    python evaluate.py

Mapeamento entre nivel de risco e rotulo:
    baixo  -> segura
    medio  -> suspeita
    alto   -> perigosa

Observacao academica: para seguranca infantil, o erro mais critico e o
falso negativo (mensagem perigosa classificada como segura). Por isso o
relatorio destaca tambem a "seguranca de recall" das classes de risco.
Nenhum dado real de crianca e utilizado: a base e inteiramente ficticia.
"""

from __future__ import annotations

import json
from pathlib import Path

from analyzer import analyze_message

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET = BASE_DIR / "data" / "simulated_messages.json"

LABELS = ("segura", "suspeita", "perigosa")
LEVEL_TO_LABEL = {"baixo": "segura", "medio": "suspeita", "alto": "perigosa"}


def load_dataset() -> list[dict[str, str]]:
    with DATASET.open("r", encoding="utf-8") as file:
        return json.load(file)


def predict_label(message: str) -> str:
    analysis = analyze_message(message)
    return LEVEL_TO_LABEL[analysis["risk_level"]]


def build_confusion(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    matrix = {actual: {pred: 0 for pred in LABELS} for actual in LABELS}
    for row in rows:
        actual = row["label"]
        predicted = predict_label(row["message"])
        matrix[actual][predicted] += 1
    return matrix


def per_class_metrics(matrix: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for label in LABELS:
        tp = matrix[label][label]
        fn = sum(matrix[label][p] for p in LABELS if p != label)
        fp = sum(matrix[a][label] for a in LABELS if a != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        metrics[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    return metrics


def accuracy(matrix: dict[str, dict[str, int]]) -> float:
    correct = sum(matrix[label][label] for label in LABELS)
    total = sum(matrix[a][p] for a in LABELS for p in LABELS)
    return correct / total if total else 0.0


def fmt_pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def print_report(rows: list[dict[str, str]]) -> None:
    matrix = build_confusion(rows)
    metrics = per_class_metrics(matrix)
    acc = accuracy(matrix)

    print("=" * 60)
    print("Guardiao Gamer - Avaliacao do classificador de risco")
    print("=" * 60)
    print(f"Base rotulada: {len(rows)} mensagens simuladas")
    print()

    print("Matriz de confusao (linhas = real, colunas = previsto)")
    header = " " * 12 + "".join(f"{label[:8]:>10}" for label in LABELS)
    print(header)
    for actual in LABELS:
        line = f"{actual:>11} " + "".join(f"{matrix[actual][p]:>10}" for p in LABELS)
        print(line)
    print()

    print("Metricas por classe")
    print(f"{'classe':>11} {'precisao':>10} {'recall':>10} {'f1':>10} {'amostras':>10}")
    for label in LABELS:
        m = metrics[label]
        print(
            f"{label:>11} {fmt_pct(m['precision']):>10} {fmt_pct(m['recall']):>10} "
            f"{fmt_pct(m['f1']):>10} {int(m['support']):>10}"
        )
    print()

    macro_f1 = sum(m["f1"] for m in metrics.values()) / len(LABELS)
    print(f"Acuracia geral : {fmt_pct(acc)}")
    print(f"F1 macro       : {fmt_pct(macro_f1)}")
    print()

    # Falsos negativos criticos: mensagem perigosa prevista como segura.
    critical_misses = matrix["perigosa"]["segura"]

    # Cobertura de alertas: toda mensagem de risco (suspeita ou perigosa) deveria
    # gerar pelo menos um alerta, ou seja, ser prevista como suspeita ou perigosa.
    risky_total = sum(metrics[label]["support"] for label in ("suspeita", "perigosa"))
    risky_alerted = sum(
        matrix[actual][pred]
        for actual in ("suspeita", "perigosa")
        for pred in ("suspeita", "perigosa")
    )
    danger_total = metrics["perigosa"]["support"]
    danger_alerted = sum(matrix["perigosa"][pred] for pred in ("suspeita", "perigosa"))

    print("Foco em seguranca infantil")
    print(f"Falsos negativos criticos (perigosa -> segura): {critical_misses}")
    if critical_misses == 0:
        print("Nenhuma mensagem perigosa passou como segura.")
    else:
        print("Atencao: ha mensagens perigosas classificadas como seguras.")
    if risky_total:
        print(
            f"Cobertura de alertas (risco que gerou alerta): "
            f"{fmt_pct(risky_alerted / risky_total)} ({risky_alerted}/{risky_total})"
        )
    if danger_total:
        print(
            f"Cobertura de alertas para mensagens perigosas: "
            f"{fmt_pct(danger_alerted / danger_total)} ({danger_alerted}/{danger_total})"
        )
    print("=" * 60)


if __name__ == "__main__":
    print_report(load_dataset())
