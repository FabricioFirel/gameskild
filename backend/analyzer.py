"""Modulo de analise de risco do Guardiao Gamer.

Este prototipo academico usa regras explicaveis para simular uma etapa de
NLP/IA. Em uma versao de pesquisa mais avancada, as mesmas entradas poderiam
alimentar um modelo treinado com scikit-learn, spaCy ou transformers.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rule:
    """Representa um grupo de padroes suspeitos e seu peso no risco final."""

    category: str
    label: str
    weight: int
    patterns: tuple[str, ...]


RULES: tuple[Rule, ...] = (
    Rule(
        category="dados_pessoais",
        label="Solicitacao de dados pessoais",
        weight=35,
        patterns=(
            "qual seu nome completo",
            "nome completo",
            "onde voce mora",
            "seu endereco",
            "qual seu endereco",
            "que escola voce estuda",
            "nome da sua escola",
            "qual sua escola",
            "seu telefone",
            "seu numero",
            "qual seu bairro",
            "manda seu contato",
            "passa seu contato",
            "passar seu contato",
            "me passar seu contato",
        ),
    ),
    Rule(
        category="sair_da_plataforma",
        label="Tentativa de levar a conversa para fora do jogo",
        weight=38,
        patterns=(
            "me chama no zap",
            "passa seu zap",
            "me chama no whatsapp",
            "chama no whatsapp",
            "vamos para o whatsapp",
            "vamos pro whatsapp",
            "me adiciona no discord",
            "passa seu discord",
            "vamos para o discord",
            "vamos pro discord",
            "me chama no instagram",
            "me adiciona no instagram",
            "passa seu instagram",
            "fala comigo fora do jogo",
            "conversar fora do jogo",
            "conversar fora daqui",
            "sair daqui",
        ),
    ),
    Rule(
        category="sigilo_isolamento",
        label="Pedido de segredo ou isolamento",
        weight=36,
        patterns=(
            "nao conta para seus pais",
            "nao conte para seus pais",
            "seus pais nao precisam saber",
            "e segredo",
            "so entre nos",
            "apaga a conversa",
            "nao fala para ninguem",
            "sem contar para ninguem",
        ),
    ),
    Rule(
        category="presentes_recompensas",
        label="Oferta de presentes ou recompensa",
        weight=22,
        patterns=(
            "te dou uma skin",
            "te dou skin",
            "te mando gift card",
            "gift card",
            "robux gratis",
            "v bucks gratis",
            "v-bucks gratis",
            "te mando pix",
            "ganhar presente",
            "codigo de premio",
            "moedas gratis",
        ),
    ),
    Rule(
        category="pedido_imagem",
        label="Pedido de foto, video ou imagem pessoal",
        weight=40,
        patterns=(
            "manda foto",
            "manda uma foto",
            "manda sua foto",
            "foto sua",
            "selfie",
            "sua selfie",
            "manda selfie",
            "mandar uma selfie",
            "manda uma selfie",
            "manda video",
            "mandar um video",
            "video seu",
            "quero te ver",
            "tira uma foto",
            "tirar uma foto",
        ),
    ),
    Rule(
        category="pressao_insistencia",
        label="Pressao ou insistencia",
        weight=16,
        patterns=(
            "responde rapido",
            "por que nao responde",
            "nao me ignora",
            "confia em mim",
            "so quero ajudar",
            "faz isso agora",
        ),
    ),
    Rule(
        category="golpe_credenciais",
        label="Possivel golpe ou roubo de credenciais",
        weight=42,
        patterns=(
            "passa sua senha",
            "me manda sua senha",
            "login e senha",
            "codigo de verificacao",
            "codigo que chegou",
            "token da conta",
            "recuperar sua conta",
        ),
    ),
)


PII_REGEXES: tuple[tuple[str, str, int], ...] = (
    ("telefone", r"\b(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}\b", 32),
    ("email", r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", 30),
    ("handle_social", r"(?<!\w)@[a-z0-9_.]{3,}", 18),
)


def normalize_text(text: str) -> str:
    """Normaliza texto para reduzir variacoes simples de escrita."""

    without_accents = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in without_accents if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def _find_rule_matches(normalized_text: str) -> tuple[list[dict[str, Any]], int]:
    matches: list[dict[str, Any]] = []
    score = 0

    for rule in RULES:
        found_terms = [pattern for pattern in rule.patterns if pattern in normalized_text]
        if found_terms:
            score += rule.weight + max(0, len(found_terms) - 1) * 4
            matches.append(
                {
                    "category": rule.category,
                    "label": rule.label,
                    "weight": rule.weight,
                    "terms": found_terms,
                }
            )

    return matches, score


def _find_pii_matches(text: str) -> tuple[list[dict[str, Any]], int]:
    matches: list[dict[str, Any]] = []
    score = 0

    for category, pattern, weight in PII_REGEXES:
        found_terms = sorted(set(re.findall(pattern, text, flags=re.IGNORECASE)))
        if found_terms:
            score += weight
            matches.append(
                {
                    "category": f"dado_detectado_{category}",
                    "label": f"Possivel dado pessoal detectado: {category}",
                    "weight": weight,
                    "terms": found_terms,
                }
            )

    return matches, score


def _behavior_bonus(
    sender_id: str | None,
    child_id: str | None,
    history: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], int]:
    """Avalia repeticao recente de abordagens para a mesma crianca."""

    if not sender_id or not child_id or not history:
        return [], 0

    risky_categories = {
        "dados_pessoais",
        "sair_da_plataforma",
        "sigilo_isolamento",
        "pedido_imagem",
        "golpe_credenciais",
    }
    repeated_hits = 0

    for item in history[-20:]:
        if item.get("sender_id") != sender_id or item.get("child_id") != child_id:
            continue

        analysis = item.get("analysis") or {}
        categories = {
            match.get("category") for match in analysis.get("matches", [])
        }
        if categories.intersection(risky_categories):
            repeated_hits += 1

    if repeated_hits >= 2:
        return [
            {
                "category": "padrao_repetido",
                "label": "Repeticao de abordagens suspeitas para a mesma crianca",
                "weight": 18,
                "terms": [f"{repeated_hits} ocorrencias anteriores"],
            }
        ], 18

    return [], 0


def _critical_combination_bonus(matches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Eleva o risco quando categorias perigosas aparecem combinadas."""

    categories = {match.get("category") for match in matches}
    bonus_matches: list[dict[str, Any]] = []
    bonus = 0

    secrecy_match = next(
        (match for match in matches if match.get("category") == "sigilo_isolamento"),
        None,
    )
    if secrecy_match and len(secrecy_match.get("terms", [])) >= 2:
        bonus += 26
        bonus_matches.append(
            {
                "category": "combinacao_critica_sigilo",
                "label": "Pedido de segredo com tentativa de ocultar a conversa",
                "weight": 26,
                "terms": ["combinacao critica: sigilo e ocultacao"],
            }
        )

    risky_pairs = [
        (
            {"presentes_recompensas", "dados_pessoais"},
            "Oferta de recompensa associada a pedido de contato ou dado pessoal",
        ),
        (
            {"sair_da_plataforma", "dados_pessoais"},
            "Contato fora da plataforma associado a pedido de dados pessoais",
        ),
        (
            {"sair_da_plataforma", "sigilo_isolamento"},
            "Contato fora da plataforma associado a segredo ou isolamento",
        ),
    ]

    for pair, label in risky_pairs:
        if pair.issubset(categories):
            bonus += 22
            bonus_matches.append(
                {
                    "category": "combinacao_critica",
                    "label": label,
                    "weight": 22,
                    "terms": ["combinacao critica"],
                }
            )

    return bonus_matches, bonus


def classify_score(score: int) -> str:
    """Converte a pontuacao numerica em nivel de risco."""

    if score >= 70:
        return "alto"
    if score >= 35:
        return "medio"
    return "baixo"


def recommendation_for(level: str) -> str:
    """Sugere uma acao humana proporcional ao risco detectado."""

    if level == "alto":
        return (
            "Bloquear ou reter a mensagem, registrar alerta imediato e solicitar "
            "revisao de um responsavel ou moderador."
        )
    if level == "medio":
        return (
            "Gerar alerta para acompanhamento, revisar o historico e orientar a "
            "crianca a nao compartilhar dados pessoais."
        )
    return "Registrar a mensagem no historico e manter acompanhamento preventivo."


def analyze_message(
    text: str,
    *,
    sender_id: str | None = None,
    child_id: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Analisa uma mensagem e retorna score, nivel, motivos e recomendacao."""

    normalized_text = normalize_text(text)
    rule_matches, score = _find_rule_matches(normalized_text)
    pii_matches, pii_score = _find_pii_matches(text)
    behavior_matches, behavior_score = _behavior_bonus(sender_id, child_id, history)

    base_matches = rule_matches + pii_matches + behavior_matches
    combo_matches, combo_score = _critical_combination_bonus(base_matches)
    matches = base_matches + combo_matches
    total_score = min(100, score + pii_score + behavior_score + combo_score)
    level = classify_score(total_score)

    return {
        "risk_level": level,
        "score": total_score,
        "matches": matches,
        "matched_terms": sorted(
            {
                term
                for match in matches
                for term in match.get("terms", [])
                if isinstance(term, str)
            }
        ),
        "recommendation": recommendation_for(level),
        "should_block": level == "alto",
    }
