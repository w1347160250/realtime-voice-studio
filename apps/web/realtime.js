// Realtime voice via Azure OpenAI Realtime (WebRTC).
// Flow: fetch ephemeral token from our backend -> setup RTCPeerConnection ->
// mic in, model audio out, transcripts over the data channel.

const rt = {
  pc: null,
  dc: null,
  micStream: null,
  audioEl: null,
  active: false,
  assistantBubble: null,
};

function rtLog(text) {
  const status = document.getElementById("voice-status");
  if (status) status.textContent = text;
  console.log("[realtime]", text);
}

function appendVoiceBubble(role, text) {
  const container = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

async function startVoice() {
  if (rt.active) return;
  rt.active = true;
  updateVoiceButton();
  rtLog("正在获取会话密钥...");

  let session;
  try {
    const res = await fetch("/api/realtime/session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.token}`,
      },
    });
    session = await res.json();
    if (!res.ok || !session.token) {
      throw new Error(session.error || "无法获取语音会话");
    }
  } catch (err) {
    rtLog("获取语音会话失败: " + err.message);
    rt.active = false;
    updateVoiceButton();
    return;
  }

  try {
    rt.pc = new RTCPeerConnection();

    // Remote audio playback (model voice).
    rt.audioEl = document.getElementById("model-audio");
    rt.pc.ontrack = (event) => {
      console.log("[realtime] ontrack:", event.track.kind, "streams:", event.streams.length);
      if (event.streams && event.streams[0]) {
        rt.audioEl.srcObject = event.streams[0];
        rt.audioEl
          .play()
          .then(() => rtLog("已连接，AI 声音已就绪，开始说话吧"))
          .catch((e) => rtLog("音频被浏览器拦截，请点一下页面: " + e.message));
      }
    };

    // Microphone capture.
    rtLog("请求麦克风权限...");
    rt.micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    rt.pc.addTrack(rt.micStream.getAudioTracks()[0]);

    // Data channel for realtime events (transcripts, etc).
    rt.dc = rt.pc.createDataChannel("realtime-channel");
    rt.dc.addEventListener("open", () => rtLog("已连接，开始说话吧"));
    rt.dc.addEventListener("message", onRealtimeEvent);
    rt.dc.addEventListener("close", () => rtLog("语音已断开"));

    // SDP offer -> Azure -> answer.
    const offer = await rt.pc.createOffer();
    await rt.pc.setLocalDescription(offer);

    const url = `${session.webrtc_url}?webrtcfilter=on`;
    const sdpRes = await fetch(url, {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${session.token}`,
        "Content-Type": "application/sdp",
      },
    });

    if (!sdpRes.ok) {
      throw new Error("SDP 交换失败: " + sdpRes.status);
    }

    const answerSdp = await sdpRes.text();
    await rt.pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
    console.log("[realtime] SDP answer set, length:", answerSdp.length);

    rt.pc.oniceconnectionstatechange = () => {
      console.log("[realtime] ICE state:", rt.pc.iceConnectionState);
    };
    rt.pc.onconnectionstatechange = () => {
      console.log("[realtime] connection state:", rt.pc.connectionState);
      rtLog("连接状态: " + rt.pc.connectionState);
      if (["failed", "disconnected", "closed"].includes(rt.pc.connectionState)) {
        stopVoice();
      }
    };
  } catch (err) {
    rtLog("语音连接失败: " + err.message);
    stopVoice();
  }
}

function onRealtimeEvent(event) {
  let msg;
  try {
    msg = JSON.parse(event.data);
  } catch {
    return;
  }
  console.log("[realtime] event:", msg.type, msg);

  switch (msg.type) {
    case "input_audio_buffer.speech_started":
      rtLog("聆听中...");
      break;
    case "conversation.item.input_audio_transcription.completed":
      if (msg.transcript) appendVoiceBubble("user", msg.transcript.trim());
      break;
    case "response.output_audio_transcript.delta":
      if (!rt.assistantBubble) {
        rt.assistantBubble = appendVoiceBubble("assistant", "");
      }
      rt.assistantBubble.textContent += msg.delta || "";
      document.getElementById("messages").scrollTop = 999999;
      break;
    case "response.output_audio_transcript.done":
      if (rt.assistantBubble && msg.transcript) {
        rt.assistantBubble.textContent = msg.transcript.trim();
      }
      rt.assistantBubble = null;
      rtLog("说完了，继续聊吧");
      break;
    case "error":
      rtLog("错误: " + (msg.error?.message || "unknown"));
      break;
    default:
      break;
  }
}

function stopVoice() {
  if (rt.dc) {
    try {
      rt.dc.close();
    } catch {}
  }
  if (rt.pc) {
    try {
      rt.pc.close();
    } catch {}
  }
  if (rt.micStream) {
    rt.micStream.getTracks().forEach((t) => t.stop());
  }
  rt.dc = null;
  rt.pc = null;
  rt.micStream = null;
  rt.assistantBubble = null;
  rt.active = false;
  updateVoiceButton();
  rtLog("语音已停止");
}

function updateVoiceButton() {
  const btn = document.getElementById("voice-btn");
  if (!btn) return;
  const label = btn.querySelector(".voice-label");
  const ico = btn.querySelector(".voice-ico");
  if (label) label.textContent = rt.active ? "停止语音" : "开始语音";
  if (ico) ico.textContent = rt.active ? "⏹" : "🎙️";
  btn.classList.toggle("recording", rt.active);
}

function toggleVoice() {
  if (rt.active) {
    stopVoice();
  } else {
    startVoice();
  }
}
