document.addEventListener("DOMContentLoaded", () => {
  const data = document.getElementById("ascii-frames-data");
  const player = document.getElementById("ascii-player");
  if (!data || !player) return;

  const frames = JSON.parse(data.textContent || "[]");
  if (!frames.length) return;

  const duration = Number(player.dataset.duration || 100);
  const toggle = document.getElementById("ascii-toggle");
  const prev = document.getElementById("ascii-prev");
  const next = document.getElementById("ascii-next");

  let index = 0;
  let playing = true;
  let timer = null;

  const fitAsciiToPanel = () => {
    const declaredColumns = Number(player.dataset.columns || 0);
    const firstLine = (frames[index] || "").split("\n")[0] || "";
    const columns = Math.max(1, declaredColumns || firstLine.length);
    const style = window.getComputedStyle(player);
    const horizontalPadding =
      Number.parseFloat(style.paddingLeft || "0") +
      Number.parseFloat(style.paddingRight || "0");
    const availableWidth = Math.max(1, player.clientWidth - horizontalPadding);
    const fontSize = Math.min(8, Math.max(0.25, availableWidth / (columns * 0.62)));
    player.style.fontSize = `${fontSize}px`;
    player.style.lineHeight = `${fontSize}px`;
  };

  const render = () => {
    player.textContent = frames[index];
    fitAsciiToPanel();
  };

  const advance = (step) => {
    index = (index + step + frames.length) % frames.length;
    render();
  };

  const start = () => {
    stop();
    timer = window.setInterval(() => advance(1), Math.max(20, duration));
  };

  const stop = () => {
    if (timer) {
      window.clearInterval(timer);
      timer = null;
    }
  };

  toggle?.addEventListener("click", () => {
    playing = !playing;
    toggle.textContent = playing ? "정지" : "재생";
    if (playing) start();
    else stop();
  });

  prev?.addEventListener("click", () => {
    stop();
    playing = false;
    if (toggle) toggle.textContent = "재생";
    advance(-1);
  });

  next?.addEventListener("click", () => {
    stop();
    playing = false;
    if (toggle) toggle.textContent = "재생";
    advance(1);
  });

  render();
  if (frames.length > 1) start();
  window.addEventListener("resize", fitAsciiToPanel);
});
