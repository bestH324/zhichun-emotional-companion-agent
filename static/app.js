// 芝春 · 情感陪伴 前端逻辑（纯原生，无构建）
const chatEl = document.getElementById("chat");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const headerMeta = document.getElementById("headerMeta");
const tokenModal = document.getElementById("tokenModal");
const tokenInput = document.getElementById("tokenInput");
const tokenSave = document.getElementById("tokenSave");

let sessionId = "";
let currentMbti = "general";

const EMOTION_EMOJI = {
  开心: "😊", 平静: "😌", 焦虑: "😟", 悲伤: "😢",
  压力大: "😣", 愤怒: "😠", 孤独: "🥺",
};

// ===== token 管理 =====
function getToken() {
  return localStorage.getItem("zhichun_token") || "";
}

function showModalIfNeeded() {
  // 有 token 或之前选择过「跳过」则不再弹窗
  if (getToken() || localStorage.getItem("zhichun_token_skipped")) {
    tokenModal.classList.add("hidden");
  } else {
    tokenModal.classList.remove("hidden");
  }
}

tokenSave.addEventListener("click", () => {
  const t = tokenInput.value.trim();
  if (t) {
    localStorage.setItem("zhichun_token", t);
    localStorage.removeItem("zhichun_token_skipped");
  } else {
    localStorage.setItem("zhichun_token_skipped", "1");
  }
  tokenModal.classList.add("hidden");
});

// ===== 消息渲染 =====
function addMessage(role, text, extra = {}) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);

  if (role === "assistant") {
    const meta = document.createElement("div");
    meta.className = "meta";
    const emoji = EMOTION_EMOJI[extra.emotion] || "🤖";
    meta.appendChild(document.createTextNode(
      `${emoji} ${extra.emotion || ""} · ${extra.mbti || currentMbti}`
    ));
    if (extra.audioPath && extra.audioPath.startsWith("/static/")) {
      const btn = document.createElement("button");
      btn.className = "audio-btn";
      btn.textContent = "🔊 播放";
      btn.addEventListener("click", () => {
        const a = new Audio(extra.audioPath);
        a.play();
      });
      meta.appendChild(btn);
    }
    wrap.appendChild(meta);
  }

  chatEl.appendChild(wrap);
  chatEl.scrollTop = chatEl.scrollHeight;
  return wrap;
}

// ===== 发送 =====
async function send() {
  const text = inputEl.value.trim();
  if (!text) return;
  sendBtn.disabled = true;
  addMessage("user", text);
  inputEl.value = "";

  try {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch("/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: sessionId,
        text,
        initial_mbti: sessionId ? null : currentMbti,
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      addMessage("assistant", `请求失败（${res.status}）：${detail}`, {});
      return;
    }

    const data = await res.json();
    sessionId = data.session_id;
    currentMbti = data.mbti;
    headerMeta.textContent = `会话 · ${data.mbti}`;

    addMessage("assistant", data.reply, {
      emotion: data.emotion?.emotion,
      mbti: data.mbti,
      audioPath: data.audio?.path,
    });
  } catch (e) {
    addMessage("assistant", "网络错误，请稍后重试。", {});
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  send();
});

showModalIfNeeded();
inputEl.focus();
