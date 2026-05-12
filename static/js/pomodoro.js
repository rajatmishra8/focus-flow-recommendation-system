let workMins = 25, breakMins = 5;
let totalSeconds, currentSeconds, interval;
let isRunning = false, isBreak = false, session = 1;
const CIRCUMFERENCE = 2 * Math.PI * 88; // r=88

function setMode(work, brk, btn) {
  workMins = work; breakMins = brk;
  document.querySelectorAll(".pomo-tab").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  resetTimer();
}

function fmt(s) {
  const m = Math.floor(s / 60), sec = s % 60;
  return `${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
}

function updateRing() {
  const pct = currentSeconds / totalSeconds;
  const offset = CIRCUMFERENCE * (1 - pct);
  document.getElementById("progressRing").style.strokeDashoffset = offset;
}

function tick() {
  currentSeconds--;
  document.getElementById("timerDisplay").textContent = fmt(currentSeconds);
  updateRing();
  if (currentSeconds <= 0) {
    clearInterval(interval);
    isRunning = false;
    if (!isBreak) {
      // Start break
      isBreak = true;
      totalSeconds = currentSeconds = breakMins * 60;
      document.getElementById("timerPhase").textContent = "Break ";
      document.getElementById("progressRing").style.stroke = "#10b981";
      notify("Break time! Rest for " + breakMins + " mins.");
      startTimer();
    } else {
      // End of break, next session
      isBreak = false;
      session = session < 4 ? session + 1 : 1;
      document.getElementById("sessionNum").textContent = session;
      totalSeconds = currentSeconds = workMins * 60;
      document.getElementById("timerPhase").textContent = "Focus ";
      document.getElementById("progressRing").style.stroke = "var(--accent)";
      document.getElementById("timerDisplay").textContent = fmt(currentSeconds);
      document.getElementById("startBtn").disabled = false;
      document.getElementById("pauseBtn").disabled = true;
      updateRing();
      notify("Focus session " + session + " — let's go!");
    }
  }
}

function startTimer() {
  if (isRunning) return;
  if (!totalSeconds) { totalSeconds = currentSeconds = workMins * 60; }
  isRunning = true;
  interval = setInterval(tick, 1000);
  document.getElementById("startBtn").disabled = true;
  document.getElementById("pauseBtn").disabled = false;
  // Request notification permission
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }
}

function pauseTimer() {
  clearInterval(interval);
  isRunning = false;
  document.getElementById("startBtn").disabled = false;
  document.getElementById("pauseBtn").disabled = true;
}

function resetTimer() {
  clearInterval(interval);
  isRunning = false; isBreak = false;
  totalSeconds = currentSeconds = workMins * 60;
  document.getElementById("timerDisplay").textContent = fmt(currentSeconds);
  document.getElementById("timerPhase").textContent = "Focus ";
  document.getElementById("progressRing").style.stroke = "var(--accent)";
  document.getElementById("progressRing").style.strokeDashoffset = "0";
  document.getElementById("startBtn").disabled = false;
  document.getElementById("pauseBtn").disabled = true;
}

function notify(msg) {
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification(" HCA-Rec Timer", { body: msg, icon: "/static/img/icon.png" });
  }
  // Audio beep
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = "sine"; osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
    osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.8);
  } catch(e) {}
}

// Init
resetTimer();