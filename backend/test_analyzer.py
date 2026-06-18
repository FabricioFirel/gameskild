"""Testes automatizados do classificador de risco do Guardiao Gamer.

Usa apenas a biblioteca padrao (unittest), sem dependencias externas.

Executar:
    cd backend
    python -m unittest

Os testes validam os requisitos do projeto academico:
- mensagens seguras devem ficar em risco baixo;
- pedido de contato externo deve gerar alerta;
- segredo, pedido de imagem e roubo de credenciais devem gerar alerta;
- combinacoes perigosas devem elevar o risco para alto;
- nenhuma mensagem perigosa deve ser classificada como segura (sem alerta).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from analyzer import analyze_message, classify_score, normalize_text

DATASET = Path(__file__).resolve().parent.parent / "data" / "simulated_messages.json"


class NormalizationTests(unittest.TestCase):
    def test_removes_accents_and_lowercases(self):
        self.assertEqual(normalize_text("Olá, MANDA Foto"), "ola, manda foto")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_text("  oi    tudo   bem "), "oi tudo bem")


class ClassificationThresholdTests(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(classify_score(0), "baixo")
        self.assertEqual(classify_score(34), "baixo")
        self.assertEqual(classify_score(35), "medio")
        self.assertEqual(classify_score(69), "medio")
        self.assertEqual(classify_score(70), "alto")
        self.assertEqual(classify_score(100), "alto")


class SafeMessageTests(unittest.TestCase):
    def test_safe_message_is_low_risk(self):
        result = analyze_message("Boa partida, vamos defender a base juntos.")
        self.assertEqual(result["risk_level"], "baixo")
        self.assertFalse(result["should_block"])

    def test_safe_message_generates_no_match(self):
        result = analyze_message("Parabens pela vitoria, foi uma jogada incrivel.")
        self.assertEqual(result["matches"], [])


class RiskyMessageTests(unittest.TestCase):
    def assert_generates_alert(self, message: str):
        result = analyze_message(message)
        self.assertIn(
            result["risk_level"],
            ("medio", "alto"),
            msg=f"Mensagem deveria gerar alerta: {message!r} -> {result['risk_level']}",
        )

    def test_external_contact_generates_alert(self):
        self.assert_generates_alert("Me chama no WhatsApp depois do jogo.")

    def test_personal_data_request_generates_alert(self):
        self.assert_generates_alert("Qual sua escola e onde voce mora?")

    def test_image_request_generates_alert(self):
        self.assert_generates_alert("Manda uma selfie sua agora.")

    def test_credential_theft_generates_alert(self):
        self.assert_generates_alert("Me passa sua senha que eu recupero sua conta.")

    def test_secrecy_request_generates_alert(self):
        self.assert_generates_alert("Nao conta para seus pais, e segredo.")


class CriticalCombinationTests(unittest.TestCase):
    def test_secrecy_and_deletion_is_high_risk(self):
        result = analyze_message("Nao conta para seus pais, e segredo. Apaga a conversa.")
        self.assertEqual(result["risk_level"], "alto")
        self.assertTrue(result["should_block"])

    def test_gift_plus_contact_is_high_risk(self):
        result = analyze_message("Te dou uma skin se voce passar seu contato.")
        self.assertEqual(result["risk_level"], "alto")

    def test_pii_regex_detects_phone(self):
        result = analyze_message("Meu numero e 11 91234-5678, me chama la.")
        categories = {match["category"] for match in result["matches"]}
        self.assertIn("dado_detectado_telefone", categories)


class BehaviorEscalationTests(unittest.TestCase):
    def test_repeated_approaches_increase_score(self):
        history = []
        for _ in range(3):
            analysis = analyze_message(
                "Qual seu endereco?",
                sender_id="suspeito-1",
                child_id="crianca-1",
                history=history,
            )
            history.append(
                {
                    "sender_id": "suspeito-1",
                    "child_id": "crianca-1",
                    "analysis": analysis,
                }
            )

        last = analyze_message(
            "Qual seu endereco?",
            sender_id="suspeito-1",
            child_id="crianca-1",
            history=history,
        )
        categories = {match["category"] for match in last["matches"]}
        self.assertIn("padrao_repetido", categories)


class DatasetSafetyTests(unittest.TestCase):
    """Garante que nenhuma mensagem perigosa da base passe como segura."""

    @classmethod
    def setUpClass(cls):
        with DATASET.open("r", encoding="utf-8") as file:
            cls.rows = json.load(file)

    def test_no_dangerous_message_is_classified_safe(self):
        level_to_label = {"baixo": "segura", "medio": "suspeita", "alto": "perigosa"}
        misses = []
        for row in self.rows:
            if row["label"] != "perigosa":
                continue
            predicted = level_to_label[analyze_message(row["message"])["risk_level"]]
            if predicted == "segura":
                misses.append(row["message"])
        self.assertEqual(misses, [], msg=f"Mensagens perigosas sem alerta: {misses}")

    def test_every_dangerous_message_generates_alert(self):
        for row in self.rows:
            if row["label"] != "perigosa":
                continue
            level = analyze_message(row["message"])["risk_level"]
            self.assertIn(level, ("medio", "alto"), msg=row["message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
