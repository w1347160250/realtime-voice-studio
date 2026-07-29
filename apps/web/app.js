const state = {
  token: localStorage.getItem("token") || "",
  username: localStorage.getItem("username") || "",
  activeSessionId: null,
};

const els = {
  loginCard: document.getElementById("login-card"),
  chatCard: document.getElementById("chat-card"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  loginBtn: document.getElementById("login-btn"),
  loginStatus: document.getElementById("login-status"),
  logoutBtn: document.getElementById("logout-btn"),
  sessions: document.getElementById("sessions"),
  messages: document.getElementById("messages"),
  messageInput: document.getElementById("message-input"),
  sendBtn: document.getElementById("send-btn"),
  newSessionBtn: document.getElementById("new-session-btn"),
  chatStatus: document.getElementById("chat-status"),
};

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${state.token}`,
  };
}

function setLoginStatus(text) {
  els.loginStatus.textContent = text;
}

function setChatStatus(text) {
  els.chatStatus.textContent = text;
}

function toggleView() {
  const loggedIn = Boolean(state.token);
  els.loginCard.classList.toggle("hidden", loggedIn);
  els.chatCard.classList.toggle("hidden", !loggedIn);
}

function renderMessages(items) {
  els.messages.innerHTML = "";
  for (const item of items) {
    const div = document.createElement("div");
    div.className = `msg ${item.role}`;
    div.textContent = item.content;
    els.messages.appendChild(div);
  }
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function loadSessions() {
  const res = await fetch("/api/sessions", { headers: authHeaders() });
  if (!res.ok) {
    throw new Error("无法加载会话");
  }
  const sessions = await res.json();

  els.sessions.innerHTML = "";
  for (const s of sessions) {
    const btn = document.createElement("button");
    btn.className = "session-item secondary";
    if (state.activeSessionId === s.id) {
      btn.classList.add("active");
    }
    btn.textContent = `${s.title}`;
    btn.onclick = async () => {
      state.activeSessionId = s.id;
      await loadMessages(s.id);
      await loadSessions();
    };
    els.sessions.appendChild(btn);
  }

  if (!state.activeSessionId && sessions.length > 0) {
    state.activeSessionId = sessions[0].id;
    await loadMessages(state.activeSessionId);
  }
}

async function loadMessages(sessionId) {
  const res = await fetch(`/api/sessions/${sessionId}/messages`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error("无法加载消息");
  }
  const messages = await res.json();
  renderMessages(messages);
}

async function login() {
  const username = els.username.value.trim();
  const password = els.password.value.trim();

  if (!username || !password) {
    setLoginStatus("用户名和密码都需要填写");
    return;
  }

  setLoginStatus("登录中...");
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();

  if (!res.ok) {
    setLoginStatus(data.error || "登录失败");
    return;
  }

  state.token = data.token;
  state.username = data.username;
  state.activeSessionId = null;
  localStorage.setItem("token", state.token);
  localStorage.setItem("username", state.username);

  toggleView();
  setChatStatus(`欢迎, ${state.username}`);
  await loadSessions();
}

function logout() {
  state.token = "";
  state.username = "";
  state.activeSessionId = null;
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  els.messages.innerHTML = "";
  els.sessions.innerHTML = "";
  setLoginStatus("已退出");
  toggleView();
}

function createNewSession() {
  state.activeSessionId = null;
  els.messages.innerHTML = "";
  setChatStatus("新会话已准备，点“开始语音”直接开聊");
}

function bindEvents() {
  els.loginBtn.addEventListener("click", () => {
    login().catch((err) => setLoginStatus(err.message));
  });

  els.logoutBtn.addEventListener("click", logout);

  els.newSessionBtn.addEventListener("click", createNewSession);

  const voiceBtn = document.getElementById("voice-btn");
  if (voiceBtn) {
    voiceBtn.addEventListener("click", () => toggleVoice());
  }
}

async function bootstrap() {
  bindEvents();
  toggleView();

  if (state.token) {
    setChatStatus(`欢迎回来, ${state.username}`);
    try {
      await loadSessions();
    } catch {
      logout();
    }
  }
}

bootstrap();
