/* Game Skild — controlador da versão demo (sem backend). */
(function () {
  "use strict";
  var GS = window.GameSkild;

  // Base rotulada simulada (igual a data/simulated_messages.json) — treina o modelo.
  var SEED_LABELED = [
    ["segura","Boa partida, vamos defender a base juntos."],
    ["segura","Voce joga bem. Vamos chamar o restante do time para a proxima rodada?"],
    ["segura","Parabens pela vitoria, foi uma jogada incrivel."],
    ["segura","Alguem quer treinar a fase dois comigo?"],
    ["segura","Gostei da sua estrategia no ultimo round."],
    ["segura","Vamos montar um time para o torneio do fim de semana?"],
    ["segura","Que skin maneira, onde voce conseguiu dentro do jogo?"],
    ["segura","Obrigado pela ajuda na missao, valeu demais."],
    ["segura","Bom jogo a todos, ate a proxima partida."],
    ["segura","Curti jogar com voce, foi divertido."],
    ["segura","Vamos revisar a tatica antes da proxima fase."],
    ["segura","Boa sorte no campeonato de amanha."],
    ["suspeita","Qual sua escola? Talvez eu conheca alguem de la."],
    ["suspeita","Me chama no WhatsApp depois do jogo."],
    ["suspeita","Onde voce mora? Sou aqui perto tambem."],
    ["suspeita","Passa seu instagram para a gente conversar fora do jogo."],
    ["suspeita","Qual seu numero? Quero te mandar uma novidade."],
    ["suspeita","Vamos para o Discord, e melhor para conversar."],
    ["suspeita","Me adiciona no instagram, fica mais facil falar."],
    ["suspeita","Responde rapido, por que nao responde?"],
    ["suspeita","Confia em mim, so quero ajudar voce."],
    ["suspeita","Vamos conversar fora do jogo, aqui tem muita gente."],
    ["suspeita","Qual seu nome completo? Quero te achar nas redes."],
    ["suspeita","Que escola voce estuda? Tenho primos perto."],
    ["perigosa","Nao conta para seus pais, e segredo. Apaga a conversa."],
    ["perigosa","Te dou uma skin se voce passar seu contato."],
    ["perigosa","Manda uma foto sua agora, quero te ver."],
    ["perigosa","Me passa sua senha que eu recupero sua conta."],
    ["perigosa","Me manda o codigo de verificacao que chegou no seu celular."],
    ["perigosa","Isso e so entre nos, nao fala para ninguem e me manda seu endereco."],
    ["perigosa","Te mando um gift card se voce mandar uma selfie."],
    ["perigosa","Vamos para o WhatsApp e nao conta para seus pais."],
    ["perigosa","Passa seu login e senha que eu te dou robux gratis."],
    ["perigosa","Apaga a conversa depois e me manda uma foto sua."],
    ["perigosa","Seus pais nao precisam saber, me passa seu numero e uma foto."],
    ["perigosa","Te dou v-bucks gratis se voce me passar seu endereco e uma selfie."]
  ];

  var STORE_KEY = "gameskild_demo_v1";
  var LEARN_KEY = "gameskild_learning_v1";

  function loadStore() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || null; } catch (e) { return null; }
  }
  function saveStore(s) { localStorage.setItem(STORE_KEY, JSON.stringify(s)); }
  function loadLearning() {
    try { return JSON.parse(localStorage.getItem(LEARN_KEY)) || []; } catch (e) { return []; }
  }
  function saveLearning(l) { localStorage.setItem(LEARN_KEY, JSON.stringify(l)); }

  var state = loadStore() || { children: [], messages: [], alerts: [] };

  // ---- Modelo (treina com a base + correções aprendidas) ----
  var model = new GS.NaiveBayes();
  function trainModel() {
    var examples = SEED_LABELED.map(function (p) {
      return { message: p[1], level: GS.LABEL_TO_LEVEL[p[0]] };
    }).concat(loadLearning());
    model.fit(examples);
  }
  trainModel();

  // ---- Análise híbrida: regras + ML (espelha app.py analyze_with_ml) ----
  function analyze(text) {
    var a = GS.analyzeRules(text);
    var ml = model.predict(text);
    a.ml = ml;
    if (GS.LEVEL_ORDER[ml.level] > GS.LEVEL_ORDER[a.risk_level]) {
      a.risk_level = ml.level;
      a.score = Math.max(a.score, GS.ML_FLOOR[ml.level]);
      a.recommendation = GS.recommendation(ml.level);
      a.should_block = ml.level === "alto";
      a.risk_source = "aprendizado_de_maquina";
      ml.influential_terms.forEach(function (t) {
        if (a.matched_terms.indexOf(t) === -1) a.matched_terms.push(t);
      });
    } else {
      a.risk_source = "regras";
    }
    return a;
  }

  function uuid() { return "id-" + Math.random().toString(36).slice(2) + Date.now().toString(36); }
  function nowIso() { return new Date().toISOString(); }

  // ---------- Helpers de UI ----------
  var $ = function (s) { return document.querySelector(s); };
  function escapeHtml(v) {
    return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  function formatDate(v) {
    if (!v) return "-";
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(v));
  }
  function riskClass(l) { return l === "alto" ? "high" : l === "medio" ? "medium" : "low"; }
  function riskLabel(l) { return ({ baixo: "Baixo", medio: "Médio", alto: "Alto" })[l] || l; }
  function highlight(message, terms) {
    var safe = escapeHtml(message);
    (terms || []).forEach(function (term) {
      if (!term || term.indexOf("ocorrencias anteriores") !== -1 || term.indexOf("combinacao") !== -1) return;
      var esc = escapeHtml(term).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      safe = safe.replace(new RegExp("(" + esc + ")", "gi"), "<mark>$1</mark>");
    });
    return safe;
  }

  var toast = $("#liveToast"), toastTimer = null;
  function showToast(text) {
    if (!toast) return;
    toast.textContent = text; toast.hidden = false; toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove("show"); toast.hidden = true; }, 4500);
  }

  // ---------- Render ----------
  function render() {
    $("#childrenCount").textContent = state.children.length;
    $("#alertsCount").textContent = state.alerts.length;
    $("#highRiskCount").textContent = state.alerts.filter(function (a) { return a.risk_level === "alto"; }).length;

    var sel = $("#childSelect");
    sel.innerHTML = "";
    if (!state.children.length) {
      sel.innerHTML = '<option value="">Cadastre uma criança fictícia</option>';
    } else {
      state.children.forEach(function (c) {
        var o = document.createElement("option");
        o.value = c.id; o.textContent = c.child_name + " (" + c.responsible_name + ")";
        sel.appendChild(o);
      });
    }

    var list = $("#alertsList");
    if (!state.alerts.length) {
      list.innerHTML = '<p class="empty">Nenhum alerta registrado ainda.</p>';
    } else {
      list.innerHTML = state.alerts.slice().reverse().map(function (al) {
        var cls = riskClass(al.risk_level);
        var terms = (al.matched_terms || []).map(function (t) { return '<span class="tag">' + escapeHtml(t) + "</span>"; }).join("");
        var src = al.risk_source === "aprendizado_de_maquina" ? '<span class="tag ml">aprendizado de máquina</span>' : "";
        var msg = escapeHtml(al.message);
        return '<article class="alert ' + cls + '">' +
          "<header><h3>" + escapeHtml(al.child_name) + " recebeu mensagem de " + escapeHtml(al.sender_name) + "</h3>" +
          '<span class="risk ' + cls + '">' + riskLabel(al.risk_level) + " · " + al.score + "/100</span></header>" +
          "<p><strong>Jogo:</strong> " + escapeHtml(al.game) + " · <strong>Data:</strong> " + formatDate(al.created_at) + "</p>" +
          "<p><strong>Mensagem:</strong> " + highlight(al.message, al.matched_terms) + "</p>" +
          "<p><strong>Recomendação:</strong> " + escapeHtml(al.recommendation) + "</p>" +
          '<div class="tags">' + src + (terms || '<span class="tag">sem termo destacado</span>') + "</div>" +
          '<div class="feedback"><span class="feedback-label">A classificação está correta?</span>' +
          '<button type="button" class="fb" data-level="' + escapeHtml(al.risk_level) + '" data-message="' + msg + '">Confirmar</button>' +
          '<button type="button" class="fb alt" data-level="baixo" data-message="' + msg + '">Baixo</button>' +
          '<button type="button" class="fb alt" data-level="medio" data-message="' + msg + '">Médio</button>' +
          '<button type="button" class="fb alt" data-level="alto" data-message="' + msg + '">Alto</button>' +
          "</div></article>";
      }).join("");
    }

    var tb = $("#messagesTable");
    if (!state.messages.length) {
      tb.innerHTML = '<tr><td colspan="6" class="empty">Nenhuma mensagem registrada.</td></tr>';
    } else {
      tb.innerHTML = state.messages.slice().reverse().map(function (it) {
        var a = it.analysis || {}; var cls = riskClass(a.risk_level);
        return "<tr><td>" + formatDate(it.created_at) + "</td><td>" + escapeHtml(it.sender_name) + "</td>" +
          "<td>" + escapeHtml(it.game) + "</td><td>" + highlight(it.message, a.matched_terms) + "</td>" +
          '<td><span class="risk ' + cls + '">' + riskLabel(a.risk_level) + " · " + a.score + "/100</span></td>" +
          "<td>" + escapeHtml(a.recommendation) + "</td></tr>";
      }).join("");
    }
  }

  function createAlertFrom(rec) {
    if (rec.analysis.risk_level === "baixo") return null;
    return { id: uuid(), message_id: rec.id, child_id: rec.child_id, sender_id: rec.sender_id,
      sender_name: rec.sender_name, child_name: rec.child_name, game: rec.game, message: rec.message,
      risk_level: rec.analysis.risk_level, score: rec.analysis.score, status: "novo",
      created_at: nowIso(), recommendation: rec.analysis.recommendation,
      matched_terms: rec.analysis.matched_terms, risk_source: rec.analysis.risk_source };
  }

  // ---------- Eventos ----------
  $("#childForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var f = new FormData(e.target);
    state.children.push({ id: uuid(), child_name: f.get("child_name"),
      responsible_name: f.get("responsible_name"), age: Number(f.get("age")) || null, created_at: nowIso() });
    saveStore(state); e.target.reset(); render();
    showToast("Criança fictícia cadastrada.");
  });

  $("#messageForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var f = new FormData(e.target);
    var childId = f.get("child_id");
    var child = state.children.filter(function (c) { return c.id === childId; })[0];
    if (!child) { showToast("Cadastre uma criança primeiro."); return; }
    var text = (f.get("message") || "").trim();
    if (!text) return;
    var senderName = (f.get("sender_name") || "Jogador desconhecido").trim();
    var rec = { id: uuid(), child_id: childId, child_name: child.child_name,
      sender_id: senderName.toLowerCase().replace(/\s+/g, "-"), sender_name: senderName,
      sender_type: f.get("sender_type"), game: (f.get("game") || "Jogo simulado").trim(),
      message: text, created_at: nowIso(), analysis: analyze(text) };
    state.messages.push(rec);
    var alert = createAlertFrom(rec);
    if (alert) {
      state.alerts.push(alert);
      showToast("Risco " + riskLabel(alert.risk_level) + " detectado: " + senderName + " (score " + alert.score + ")");
    } else {
      showToast("Mensagem registrada (risco baixo).");
    }
    saveStore(state); e.target.reset(); render();
  });

  $("#alertsList").addEventListener("click", function (e) {
    var btn = e.target.closest("button.fb");
    if (!btn) return;
    var learning = loadLearning();
    learning.push({ message: btn.dataset.message, level: btn.dataset.level, source: "responsavel", created_at: nowIso() });
    saveLearning(learning);
    trainModel();
    btn.disabled = true;
    showToast("O Game Skild aprendeu com a sua correção.");
  });

  $("#seedButton").addEventListener("click", function () {
    var childId = uuid();
    state = { children: [{ id: childId, child_name: "Crianca Simulada",
      responsible_name: "Responsavel Simulado", age: 11, created_at: nowIso() }], messages: [], alerts: [] };
    var examples = [
      ["PlayerLegal", "jogador", "Arena Escolar", "Boa partida, vamos defender a base juntos."],
      ["ContatoFora", "desconhecido", "Arena Escolar", "Me chama no WhatsApp depois do jogo."],
      ["Presenteiro", "desconhecido", "Mundo dos Blocos", "Te dou uma skin se voce passar seu contato."],
      ["Segredo", "adulto_suspeito", "Mundo dos Blocos", "Nao conta para seus pais, e segredo. Apaga a conversa. Manda uma foto sua."]
    ];
    examples.forEach(function (ex) {
      var rec = { id: uuid(), child_id: childId, child_name: "Crianca Simulada",
        sender_id: ex[0].toLowerCase(), sender_name: ex[0], sender_type: ex[1], game: ex[2],
        message: ex[3], created_at: nowIso(), analysis: analyze(ex[3]) };
      state.messages.push(rec);
      var alert = createAlertFrom(rec);
      if (alert) state.alerts.push(alert);
    });
    saveStore(state); render();
    showToast("Exemplos carregados.");
  });

  render();
})();
