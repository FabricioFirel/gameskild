"""Classificador de aprendizado de maquina do Game Skild.

Implementa um Naive Bayes multinomial em Python puro (sem dependencias
externas) que aprende a estimar o nivel de risco de uma mensagem a partir de
exemplos rotulados. O modelo aprende de duas fontes:

1. Base inicial de exemplos simulados (`data/simulated_messages.json`).
2. Correcoes humanas registradas ao longo do uso (`data/learning_data.json`).

Sempre que um responsavel confirma ou corrige um alerta, o exemplo entra na
base de aprendizado e o modelo e re-treinado. Assim o sistema melhora com o que
acontece, em vez de depender apenas de regras fixas.

Mantemos o resultado explicavel: alem do nivel previsto, devolvemos os termos
que mais pesaram na decisao.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SEED_FILE = DATA_DIR / "simulated_messages.json"
LEARNING_FILE = DATA_DIR / "learning_data.json"

# Niveis de risco em ordem crescente de severidade.
LEVELS = ("baixo", "medio", "alto")
LEVEL_ORDER = {level: index for index, level in enumerate(LEVELS)}

# Os rotulos da base simulada usam outra nomenclatura.
LABEL_TO_LEVEL = {"segura": "baixo", "suspeita": "medio", "perigosa": "alto"}


def normalize_text(text: str) -> str:
    """Remove acentos e padroniza o texto (igual ao usado nas regras)."""

    decomposed = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def tokenize(text: str) -> list[str]:
    """Quebra o texto em palavras simples, ignorando pontuacao."""

    return re.findall(r"[a-z0-9]+", normalize_text(text))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_seed_examples() -> list[dict[str, str]]:
    """Carrega a base simulada e converte os rotulos para niveis de risco."""

    if not SEED_FILE.exists():
        return []

    with SEED_FILE.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    examples: list[dict[str, str]] = []
    for item in raw:
        level = LABEL_TO_LEVEL.get(item.get("label", ""))
        message = item.get("message", "")
        if level and message:
            examples.append({"message": message, "level": level})
    return examples


def load_learning_examples() -> list[dict[str, Any]]:
    """Carrega as correcoes humanas acumuladas (pode estar vazio)."""

    if not LEARNING_FILE.exists():
        return []

    with LEARNING_FILE.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []


def _save_learning_examples(examples: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LEARNING_FILE.open("w", encoding="utf-8") as file:
        json.dump(examples, file, ensure_ascii=False, indent=2)


class NaiveBayesClassifier:
    """Naive Bayes multinomial com suavizacao de Laplace."""

    def __init__(self) -> None:
        self.vocabulary: set[str] = set()
        self.class_doc_counts: dict[str, int] = defaultdict(int)
        self.class_token_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.class_total_tokens: dict[str, int] = defaultdict(int)
        self.total_docs = 0
        self.trained = False

    def fit(self, examples: list[dict[str, Any]]) -> None:
        """Treina o modelo a partir de uma lista de {message, level}."""

        self.__init__()  # zera o estado anterior

        for example in examples:
            level = example.get("level")
            if level not in LEVEL_ORDER:
                continue
            tokens = tokenize(example.get("message", ""))
            if not tokens:
                continue

            self.total_docs += 1
            self.class_doc_counts[level] += 1
            for token in tokens:
                self.vocabulary.add(token)
                self.class_token_counts[level][token] += 1
                self.class_total_tokens[level] += 1

        self.trained = self.total_docs > 0

    def _token_log_prob(self, token: str, level: str) -> float:
        """log P(token | nivel) com suavizacao de Laplace."""

        numerator = self.class_token_counts[level].get(token, 0) + 1
        denominator = self.class_total_tokens[level] + len(self.vocabulary)
        return math.log(numerator / denominator)

    def predict(self, text: str) -> dict[str, Any]:
        """Retorna nivel previsto, probabilidades e termos mais influentes."""

        tokens = tokenize(text)

        if not self.trained or not tokens:
            return {
                "level": "baixo",
                "confidence": 0.0,
                "probabilities": {level: 0.0 for level in LEVELS},
                "influential_terms": [],
                "trained": self.trained,
            }

        log_scores: dict[str, float] = {}
        for level in LEVELS:
            prior = self.class_doc_counts.get(level, 0)
            # Suavizamos tambem a probabilidade a priori para evitar zero.
            log_score = math.log((prior + 1) / (self.total_docs + len(LEVELS)))
            for token in tokens:
                log_score += self._token_log_prob(token, level)
            log_scores[level] = log_score

        # Converte log-scores em probabilidades normalizadas (softmax estavel).
        max_log = max(log_scores.values())
        exp_scores = {
            level: math.exp(score - max_log) for level, score in log_scores.items()
        }
        total = sum(exp_scores.values()) or 1.0
        probabilities = {level: exp_scores[level] / total for level in LEVELS}

        predicted = max(probabilities, key=probabilities.get)

        return {
            "level": predicted,
            "confidence": round(probabilities[predicted], 4),
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "influential_terms": self._influential_terms(tokens, predicted),
            "trained": True,
        }

    def _influential_terms(self, tokens: list[str], level: str) -> list[str]:
        """Termos que mais empurraram a mensagem para o nivel previsto."""

        if level == "baixo":
            return []

        scored: list[tuple[float, str]] = []
        seen: set[str] = set()
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            target = self._token_log_prob(token, level)
            others = max(
                self._token_log_prob(token, other)
                for other in LEVELS
                if other != level
            )
            advantage = target - others
            if advantage > 0:
                scored.append((advantage, token))

        scored.sort(reverse=True)
        return [token for _, token in scored[:5]]


# Instancia compartilhada, treinada na importacao e re-treinada em feedback.
_classifier = NaiveBayesClassifier()


def _all_examples() -> list[dict[str, Any]]:
    return _load_seed_examples() + [
        {"message": item.get("message", ""), "level": item.get("level")}
        for item in load_learning_examples()
    ]


def train() -> dict[str, Any]:
    """(Re)treina o modelo com base simulada + correcoes humanas."""

    examples = _all_examples()
    _classifier.fit(examples)
    return {
        "trained": _classifier.trained,
        "total_examples": len(examples),
        "seed_examples": len(_load_seed_examples()),
        "learned_examples": len(load_learning_examples()),
        "vocabulary": len(_classifier.vocabulary),
    }


def predict(text: str) -> dict[str, Any]:
    """Estima o nivel de risco aprendido para uma mensagem."""

    if not _classifier.trained:
        train()
    return _classifier.predict(text)


def add_feedback(message: str, level: str, source: str = "humano") -> dict[str, Any]:
    """Registra uma correcao humana e re-treina o modelo na hora."""

    if level not in LEVEL_ORDER:
        raise ValueError(f"Nivel invalido: {level!r}. Use um de {LEVELS}.")

    message = (message or "").strip()
    if not message:
        raise ValueError("Mensagem vazia nao pode ser usada como aprendizado.")

    examples = load_learning_examples()
    examples.append(
        {
            "message": message,
            "level": level,
            "source": source,
            "created_at": now_iso(),
        }
    )
    _save_learning_examples(examples)

    stats = train()
    stats["feedback_registered"] = True
    return stats


# Treina ao importar para que a primeira predicao ja funcione.
train()
