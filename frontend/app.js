const API_BASE = "";

const childForm = document.querySelector("#childForm");
const messageForm = document.querySelector("#messageForm");
const childSelect = document.querySelector("#childSelect");
const alertsList = document.querySelector("#alertsList");
const messagesTable = document.querySelector("#messagesTable");
const seedButton = document.querySelector("#seedButton");
const mobileUrls = document.querySelector("#mobileUrls");

let children = [];
let alerts = [];
let messages = [];
let networkInfo = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function riskClass(level) {
  if (level === "alto") return "high";
  if (level === "medio") return "medium";
  return "low";
}

function riskLabel(level) {
  return { baixo: "Baixo", medio: "Médio", alto: "Alto" }[level] || level;
}

function highlightTerms(message, terms) {
  let safeMessage = escapeHtml(message);

  for (const term of terms || []) {
    if (!term || term.includes("ocorrencias anteriores")) continue;
    const escapedTerm = escapeHtml(term);
    const expression = new RegExp(`(${escapedTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    safeMessage = safeMessage.replace(expression, "<mark>$1</mark>");
  }

  return safeMessage;
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Erro ao comunicar com a API.");
  }
  return payload;
}

async function loadData() {
  [children, alerts, messages, networkInfo] = await Promise.all([
    api("/api/children"),
    api("/api/alerts"),
    api("/api/messages"),
    api("/api/network").catch(() => null),
  ]);
  render();
}

function renderNetworkInfo() {
  if (!mobileUrls) return;

  const urls = [
    ...(networkInfo?.lan_urls || []),
    networkInfo?.current_url,
  ].filter(Boolean);
  const uniqueUrls = [...new Set(urls)];

  if (!uniqueUrls.length) {
    mobileUrls.innerHTML = "<span>Nenhum endereço de rede encontrado.</span>";
    return;
  }

  mobileUrls.innerHTML = uniqueUrls
    .map(
      (url) => `
        <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">
          ${escapeHtml(url)}
        </a>
      `,
    )
    .join("");
}

function renderStats() {
  document.querySelector("#childrenCount").textContent = children.length;
  document.querySelector("#alertsCount").textContent = alerts.length;
  document.querySelector("#highRiskCount").textContent = alerts.filter(
    (alert) => alert.risk_level === "alto",
  ).length;
}

function renderChildrenSelect() {
  childSelect.innerHTML = "";

  if (!children.length) {
    childSelect.innerHTML = '<option value="">Cadastre uma criança fictícia</option>';
    return;
  }

  for (const child of children) {
    const option = document.createElement("option");
    option.value = child.id;
    option.textContent = `${child.child_name} (${child.responsible_name})`;
    childSelect.appendChild(option);
  }
}

function renderAlerts() {
  if (!alerts.length) {
    alertsList.innerHTML = '<p class="empty">Nenhum alerta registrado ainda.</p>';
    return;
  }

  alertsList.innerHTML = alerts
    .slice()
    .reverse()
    .map((alert) => {
      const levelClass = riskClass(alert.risk_level);
      const terms = (alert.matched_terms || [])
        .map((term) => `<span class="tag">${escapeHtml(term)}</span>`)
        .join("");

      const source =
        alert.risk_source === "aprendizado_de_maquina"
          ? '<span class="tag ml">aprendizado de máquina</span>'
          : "";
      const encodedMessage = escapeHtml(alert.message);

      return `
        <article class="alert ${levelClass}">
          <header>
            <h3>${escapeHtml(alert.child_name)} recebeu mensagem de ${escapeHtml(alert.sender_name)}</h3>
            <span class="risk ${levelClass}">${riskLabel(alert.risk_level)} · ${alert.score}/100</span>
          </header>
          <p><strong>Jogo:</strong> ${escapeHtml(alert.game)} · <strong>Data:</strong> ${formatDate(alert.created_at)}</p>
          <p><strong>Mensagem:</strong> ${highlightTerms(alert.message, alert.matched_terms)}</p>
          <p><strong>Recomendação:</strong> ${escapeHtml(alert.recommendation)}</p>
          ${alert.should_block ? "<p><strong>Ação:</strong> mensagem deve ser bloqueada ou retida para revisão.</p>" : ""}
          <div class="tags">${source}${terms || '<span class="tag">sem termo destacado</span>'}</div>
          <div class="feedback">
            <span class="feedback-label">A classificação está correta?</span>
            <button type="button" class="fb" data-level="${escapeHtml(alert.risk_level)}" data-message="${encodedMessage}">Confirmar</button>
            <button type="button" class="fb alt" data-level="baixo" data-message="${encodedMessage}">Baixo</button>
            <button type="button" class="fb alt" data-level="medio" data-message="${encodedMessage}">Médio</button>
            <button type="button" class="fb alt" data-level="alto" data-message="${encodedMessage}">Alto</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderMessages() {
  if (!messages.length) {
    messagesTable.innerHTML = '<tr><td colspan="6" class="empty">Nenhuma mensagem registrada.</td></tr>';
    return;
  }

  messagesTable.innerHTML = messages
    .slice()
    .reverse()
    .map((item) => {
      const analysis = item.analysis || {};
      const levelClass = riskClass(analysis.risk_level);
      const terms = analysis.matched_terms || [];

      return `
        <tr>
          <td data-label="Data">${formatDate(item.created_at)}</td>
          <td data-label="Usuario">${escapeHtml(item.sender_name)}</td>
          <td data-label="Jogo">${escapeHtml(item.game)}</td>
          <td data-label="Mensagem">${highlightTerms(item.message, terms)}</td>
          <td data-label="Risco"><span class="risk ${levelClass}">${riskLabel(analysis.risk_level)} · ${analysis.score}/100</span></td>
          <td data-label="Acao sugerida">${escapeHtml(analysis.recommendation)}</td>
        </tr>
      `;
    })
    .join("");
}

function render() {
  renderStats();
  renderNetworkInfo();
  renderChildrenSelect();
  renderAlerts();
  renderMessages();
}

childForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(childForm);

  await api("/api/children", {
    method: "POST",
    body: JSON.stringify({
      child_name: form.get("child_name"),
      responsible_name: form.get("responsible_name"),
      age: Number(form.get("age")) || null,
    }),
  });

  childForm.reset();
  await loadData();
});

messageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(messageForm);

  await api("/api/messages", {
    method: "POST",
    body: JSON.stringify({
      child_id: form.get("child_id"),
      sender_name: form.get("sender_name"),
      sender_type: form.get("sender_type"),
      game: form.get("game"),
      message: form.get("message"),
    }),
  });

  messageForm.reset();
  await loadData();
});

seedButton.addEventListener("click", async () => {
  await api("/api/seed", { method: "POST", body: "{}" });
  await loadData();
});

// --- Feedback: ensina o modelo a partir da revisão humana ---
alertsList.addEventListener("click", async (event) => {
  const button = event.target.closest("button.fb");
  if (!button) return;

  const message = button.dataset.message;
  const level = button.dataset.level;
  button.disabled = true;

  try {
    await api("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ message, level }),
    });
    showToast(`Modelo atualizado: aprendeu "${riskLabel(level)}".`);
  } catch (error) {
    showToast(error.message);
    button.disabled = false;
  }
});

// --- Aviso visual em tempo real ---
const liveToast = document.querySelector("#liveToast");
let toastTimer = null;

function showToast(text) {
  if (!liveToast) return;
  liveToast.textContent = text;
  liveToast.hidden = false;
  liveToast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    liveToast.classList.remove("show");
    liveToast.hidden = true;
  }, 5000);
}

// --- Canal 1: SSE (notificação em tempo real com o painel aberto) ---
function connectStream() {
  const source = new EventSource(`${API_BASE}/api/stream`);

  source.addEventListener("alert", (event) => {
    const data = JSON.parse(event.data);
    const title = `Risco ${riskLabel(data.risk_level)} no ${data.game}`;
    const body = `${data.sender_name}: "${data.message}" (score ${data.score}/100)`;

    showToast(`${title} — ${data.sender_name}`);

    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body, icon: "icon-192.png" });
    }

    loadData().catch(() => {});
  });

  source.onerror = () => {
    source.close();
    setTimeout(connectStream, 5000); // reconecta se a conexão cair
  };
}

// --- Canal 2: Web Push (notificação com o app fechado) ---
function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
}

async function enableWebPush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    showToast("Este navegador não suporta Web Push.");
    return;
  }

  const registration = await navigator.serviceWorker.register("sw.js");
  const { public_key: publicKey } = await api("/api/push/public-key");

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });

  await api("/api/push/subscribe", {
    method: "POST",
    body: JSON.stringify(subscription),
  });
}

const notifyButton = document.querySelector("#notifyButton");
notifyButton?.addEventListener("click", async () => {
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      showToast("Permissão de notificação negada.");
      return;
    }
    await enableWebPush();
    showToast("Notificações ativadas com sucesso.");
    notifyButton.textContent = "Notificações ativas";
    notifyButton.disabled = true;
  } catch (error) {
    showToast(error.message || "Não foi possível ativar as notificações.");
  }
});

loadData()
  .then(connectStream)
  .catch((error) => {
    alertsList.innerHTML = `<p class="empty">${escapeHtml(error.message)}</p>`;
  });
