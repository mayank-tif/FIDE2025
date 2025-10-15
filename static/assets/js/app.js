// assets/js/app.js

// =============================
// Message Notification System
// =============================
document.addEventListener("DOMContentLoaded", () => {
  // 1️⃣ Create the message container (only once)
  if (!document.getElementById("message-container")) {
    const container = document.createElement("div");
    container.id = "message-container";
    Object.assign(container.style, {
      position: "fixed",
      top: "20px",
      right: "20px",
      zIndex: "9999"
    });
    document.body.appendChild(container);
  }

  // 2️⃣ Inject styles (only once)
  if (!document.getElementById("message-style")) {
    const style = document.createElement("style");
    style.id = "message-style";
    style.textContent = `
      .message {
        background-color: #4caf50;
        color: white;
        padding: 12px 20px;
        margin-bottom: 10px;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.4s ease-in-out;
        min-width: 220px;
        font-size: 14px;
      }
      .message.error { background-color: #f44336; }
      .message.info { background-color: #2196f3; }
      .message.warning { background-color: #ff9800; }
      .message.show { opacity: 1; transform: translateX(0); }
    `;
    document.head.appendChild(style);
  }
});

// ✅ Global function (available in all templates)
window.showMessage = function (msg, type = "success", duration = 4000) {
  const container = document.getElementById("message-container");
  if (!container) return console.error("Message container not found.");

  const el = document.createElement("div");
  el.className = `message ${type}`;
  el.textContent = msg;
  container.appendChild(el);

  // Animate in
  setTimeout(() => el.classList.add("show"), 10);

  // Auto-remove
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 800);
  }, duration);
};