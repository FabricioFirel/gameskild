// Service Worker do Game Skild — responsavel pelas notificacoes Web Push.
// Mantem o app capaz de avisar o responsavel mesmo fechado ou com o
// celular bloqueado (requer PWA instalada e HTTPS/localhost).

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (error) {
    data = { title: "Game Skild", body: event.data ? event.data.text() : "" };
  }

  const title = data.title || "Game Skild";
  const options = {
    body: data.body || "Novo alerta de risco detectado.",
    icon: "icon-192.png",
    badge: "icon-192.png",
    tag: "game-skild-alert",
    renotify: true,
    data,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow("/");
    }),
  );
});
