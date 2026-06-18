/*
 * Game Skild — motor de análise (versão demo, sem backend).
 * Porta fiel de backend/analyzer.py (regras + PII + combinações) e de
 * backend/classifier.py (Naive Bayes que aprende com correções humanas).
 * Tudo roda no navegador; o aprendizado é salvo no localStorage.
 */
(function (global) {
  "use strict";

  // ---------- Normalização e tokenização ----------
  function normalize(text) {
    return (text || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }
  function tokenize(text) {
    return normalize(text).match(/[a-z0-9]+/g) || [];
  }

  // ---------- Regras (espelha analyzer.py) ----------
  var RULES = [
    { category: "dados_pessoais", label: "Solicitacao de dados pessoais", weight: 35, patterns: [
      "qual seu nome completo","nome completo","onde voce mora","seu endereco","qual seu endereco",
      "que escola voce estuda","nome da sua escola","qual sua escola","seu telefone","seu numero",
      "qual seu bairro","manda seu contato","passa seu contato","passar seu contato","me passar seu contato"] },
    { category: "sair_da_plataforma", label: "Tentativa de levar a conversa para fora do jogo", weight: 38, patterns: [
      "me chama no zap","passa seu zap","me chama no whatsapp","chama no whatsapp","vamos para o whatsapp",
      "vamos pro whatsapp","me adiciona no discord","passa seu discord","vamos para o discord","vamos pro discord",
      "me chama no instagram","me adiciona no instagram","passa seu instagram","fala comigo fora do jogo",
      "conversar fora do jogo","conversar fora daqui","sair daqui"] },
    { category: "sigilo_isolamento", label: "Pedido de segredo ou isolamento", weight: 36, patterns: [
      "nao conta para seus pais","nao conte para seus pais","seus pais nao precisam saber","e segredo",
      "so entre nos","apaga a conversa","nao fala para ninguem","sem contar para ninguem"] },
    { category: "presentes_recompensas", label: "Oferta de presentes ou recompensa", weight: 22, patterns: [
      "te dou uma skin","te dou skin","te mando gift card","gift card","robux gratis","v bucks gratis",
      "v-bucks gratis","te mando pix","ganhar presente","codigo de premio","moedas gratis"] },
    { category: "pedido_imagem", label: "Pedido de foto, video ou imagem pessoal", weight: 40, patterns: [
      "manda foto","manda uma foto","manda sua foto","foto sua","selfie","sua selfie","manda selfie",
      "mandar uma selfie","manda uma selfie","manda video","mandar um video","video seu","quero te ver",
      "tira uma foto","tirar uma foto"] },
    { category: "pressao_insistencia", label: "Pressao ou insistencia", weight: 16, patterns: [
      "responde rapido","por que nao responde","nao me ignora","confia em mim","so quero ajudar","faz isso agora"] },
    { category: "golpe_credenciais", label: "Possivel golpe ou roubo de credenciais", weight: 42, patterns: [
      "passa sua senha","me manda sua senha","login e senha","codigo de verificacao","codigo que chegou",
      "token da conta","recuperar sua conta"] }
  ];

  var PII = [
    { category: "telefone", weight: 32, re: /(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}/gi },
    { category: "email", weight: 30, re: /[\w.+-]+@[\w.-]+\.[a-z]{2,}/gi },
    { category: "handle_social", weight: 18, re: /(?:^|[^\w])@[a-z0-9_.]{3,}/gi }
  ];

  function findRuleMatches(norm) {
    var matches = [], score = 0;
    RULES.forEach(function (rule) {
      var found = rule.patterns.filter(function (p) { return norm.indexOf(p) !== -1; });
      if (found.length) {
        score += rule.weight + Math.max(0, found.length - 1) * 4;
        matches.push({ category: rule.category, label: rule.label, weight: rule.weight, terms: found });
      }
    });
    return { matches: matches, score: score };
  }

  function findPiiMatches(text) {
    var matches = [], score = 0;
    PII.forEach(function (p) {
      var found = (text.match(p.re) || []).map(function (s) { return s.replace(/^[^\w@]+/, "").trim(); });
      found = found.filter(function (v, i, a) { return v && a.indexOf(v) === i; });
      if (found.length) {
        score += p.weight;
        matches.push({ category: "dado_detectado_" + p.category,
          label: "Possivel dado pessoal detectado: " + p.category, weight: p.weight, terms: found });
      }
    });
    return { matches: matches, score: score };
  }

  function criticalCombinations(matches) {
    var cats = {}; matches.forEach(function (m) { cats[m.category] = m; });
    var bonus = 0, extra = [];
    var secrecy = cats["sigilo_isolamento"];
    if (secrecy && secrecy.terms.length >= 2) {
      bonus += 26;
      extra.push({ category: "combinacao_critica_sigilo",
        label: "Pedido de segredo com tentativa de ocultar a conversa", weight: 26,
        terms: ["combinacao critica: sigilo e ocultacao"] });
    }
    var pairs = [
      [["presentes_recompensas","dados_pessoais"], "Oferta de recompensa associada a pedido de contato ou dado pessoal"],
      [["sair_da_plataforma","dados_pessoais"], "Contato fora da plataforma associado a pedido de dados pessoais"],
      [["sair_da_plataforma","sigilo_isolamento"], "Contato fora da plataforma associado a segredo ou isolamento"]
    ];
    pairs.forEach(function (pair) {
      if (pair[0].every(function (c) { return cats[c]; })) {
        bonus += 22;
        extra.push({ category: "combinacao_critica", label: pair[1], weight: 22, terms: ["combinacao critica"] });
      }
    });
    return { matches: extra, score: bonus };
  }

  function classify(score) { return score >= 70 ? "alto" : score >= 35 ? "medio" : "baixo"; }
  function recommendation(level) {
    if (level === "alto") return "Bloquear ou reter a mensagem, registrar alerta imediato e solicitar revisao de um responsavel ou moderador.";
    if (level === "medio") return "Gerar alerta para acompanhamento, revisar o historico e orientar a crianca a nao compartilhar dados pessoais.";
    return "Registrar a mensagem no historico e manter acompanhamento preventivo.";
  }

  function analyzeRules(text) {
    var norm = normalize(text);
    var r = findRuleMatches(norm);
    var pii = findPiiMatches(text);
    var base = r.matches.concat(pii.matches);
    var combo = criticalCombinations(base);
    var matches = base.concat(combo.matches);
    var total = Math.min(100, r.score + pii.score + combo.score);
    var level = classify(total);
    var terms = [];
    matches.forEach(function (m) { (m.terms || []).forEach(function (t) {
      if (typeof t === "string" && terms.indexOf(t) === -1) terms.push(t); }); });
    return { risk_level: level, score: total, matches: matches, matched_terms: terms,
      recommendation: recommendation(level), should_block: level === "alto" };
  }

  // ---------- Naive Bayes (espelha classifier.py) ----------
  var LEVELS = ["baixo", "medio", "alto"];
  var LEVEL_ORDER = { baixo: 0, medio: 1, alto: 2 };
  var LABEL_TO_LEVEL = { segura: "baixo", suspeita: "medio", perigosa: "alto" };

  function NaiveBayes() { this.reset(); }
  NaiveBayes.prototype.reset = function () {
    this.vocab = {}; this.vocabSize = 0; this.docCounts = {}; this.tokenCounts = {};
    this.totalTokens = {}; this.totalDocs = 0; this.trained = false;
    var self = this; LEVELS.forEach(function (l) {
      self.docCounts[l] = 0; self.tokenCounts[l] = {}; self.totalTokens[l] = 0; });
  };
  NaiveBayes.prototype.fit = function (examples) {
    this.reset(); var self = this;
    examples.forEach(function (ex) {
      if (LEVEL_ORDER[ex.level] === undefined) return;
      var toks = tokenize(ex.message); if (!toks.length) return;
      self.totalDocs++; self.docCounts[ex.level]++;
      toks.forEach(function (t) {
        if (!self.vocab[t]) { self.vocab[t] = 1; self.vocabSize++; }
        self.tokenCounts[ex.level][t] = (self.tokenCounts[ex.level][t] || 0) + 1;
        self.totalTokens[ex.level]++;
      });
    });
    this.trained = this.totalDocs > 0;
  };
  NaiveBayes.prototype.tokenLogProb = function (token, level) {
    var num = (this.tokenCounts[level][token] || 0) + 1;
    var den = this.totalTokens[level] + this.vocabSize;
    return Math.log(num / den);
  };
  NaiveBayes.prototype.predict = function (text) {
    var toks = tokenize(text), self = this;
    if (!this.trained || !toks.length)
      return { level: "baixo", confidence: 0, probabilities: { baixo: 0, medio: 0, alto: 0 }, influential_terms: [], trained: this.trained };
    var logs = {};
    LEVELS.forEach(function (level) {
      var prior = self.docCounts[level];
      var s = Math.log((prior + 1) / (self.totalDocs + LEVELS.length));
      toks.forEach(function (t) { s += self.tokenLogProb(t, level); });
      logs[level] = s;
    });
    var maxLog = Math.max.apply(null, LEVELS.map(function (l) { return logs[l]; }));
    var exp = {}, total = 0;
    LEVELS.forEach(function (l) { exp[l] = Math.exp(logs[l] - maxLog); total += exp[l]; });
    var probs = {}; LEVELS.forEach(function (l) { probs[l] = exp[l] / (total || 1); });
    var predicted = LEVELS.reduce(function (a, b) { return probs[b] > probs[a] ? b : a; }, "baixo");
    return { level: predicted, confidence: Math.round(probs[predicted] * 1e4) / 1e4,
      probabilities: probs, influential_terms: this.influential(toks, predicted), trained: true };
  };
  NaiveBayes.prototype.influential = function (toks, level) {
    if (level === "baixo") return [];
    var self = this, seen = {}, scored = [];
    toks.forEach(function (t) {
      if (seen[t]) return; seen[t] = 1;
      var target = self.tokenLogProb(t, level);
      var others = Math.max.apply(null, LEVELS.filter(function (l) { return l !== level; })
        .map(function (l) { return self.tokenLogProb(t, l); }));
      if (target - others > 0) scored.push([target - others, t]);
    });
    scored.sort(function (a, b) { return b[0] - a[0]; });
    return scored.slice(0, 5).map(function (x) { return x[1]; });
  };

  global.GameSkild = {
    normalize: normalize,
    analyzeRules: analyzeRules,
    NaiveBayes: NaiveBayes,
    LEVELS: LEVELS,
    LEVEL_ORDER: LEVEL_ORDER,
    LABEL_TO_LEVEL: LABEL_TO_LEVEL,
    ML_FLOOR: { baixo: 0, medio: 35, alto: 70 },
    recommendation: recommendation
  };
})(window);
