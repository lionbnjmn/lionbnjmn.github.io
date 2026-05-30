(() => {
  // "without_replacement": each item shown at most once per cycle; resets when all seen.
  // "with_replacement":    each roll is independent (items may repeat).
  const SAMPLING_MODE = "without_replacement";

  const overlay = document.getElementById("lottery-overlay");
  const slotEl = document.getElementById("lottery-media-slot");
  const descriptionEl = document.getElementById("lottery-description");
  const rarityEl = document.getElementById("lottery-rarity");
  const openBtn = document.getElementById("open-lottery");
  const closeBtn = document.getElementById("close-lottery");
  const rollBtn = document.getElementById("roll-button");

  document.querySelectorAll("body > video").forEach((v) => {
    v.addEventListener("mouseenter", () => {
      v.muted = false;
      v.play().catch(() => {});
    });
    v.addEventListener("mouseleave", () => {
      v.muted = true;
    });
  });

  let lotteryData = null;

  async function loadLotteryData() {
    if (lotteryData) return lotteryData;
    const res = await fetch("lottery_index.json", { cache: "no-cache" });
    if (!res.ok)
      throw new Error(`Failed to load lottery_index.json: ${res.status}`);
    lotteryData = await res.json();
    return lotteryData;
  }

  function pickWeighted(items, weights) {
    const totals = items.map((it) => weights[it.rarity] ?? 1);
    const sum = totals.reduce((a, b) => a + b, 0);
    let r = Math.random() * sum;
    for (let i = 0; i < items.length; i++) {
      r -= totals[i];
      if (r < 0) return items[i];
    }
    return items[items.length - 1];
  }

  const SEEN_KEY = "lottery.seen.v1";

  function itemKey(item) {
    if (item.id !== undefined && item.id !== null) return String(item.id);
    return item.src || item.href || JSON.stringify(item);
  }

  function loadSeen() {
    try {
      const raw = localStorage.getItem(SEEN_KEY);
      return new Set(raw ? JSON.parse(raw) : []);
    } catch (_) {
      return new Set();
    }
  }

  function saveSeen(set) {
    try {
      localStorage.setItem(SEEN_KEY, JSON.stringify([...set]));
    } catch (_) {}
  }

  function pickWithoutReplacement(items, weights) {
    let seen = loadSeen();
    let pool = items.filter((it) => !seen.has(itemKey(it)));
    if (pool.length === 0) {
      seen = new Set();
      pool = items;
    }
    const pick = pickWeighted(pool, weights);
    seen.add(itemKey(pick));
    saveSeen(seen);
    return pick;
  }

  function pickItem(items, weights) {
    if (SAMPLING_MODE === "without_replacement") {
      return pickWithoutReplacement(items, weights);
    }
    return pickWeighted(items, weights);
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function preloadImages(srcs) {
    srcs.forEach((src) => {
      const img = new Image();
      img.src = src;
    });
  }

  async function spinAnimation({ pool, frames = 20, totalMs = 1800 }) {
    if (!pool || pool.length === 0) return;

    clearResult();
    const img = document.createElement("img");
    img.alt = "";
    slotEl.appendChild(img);

    // decelerate: gap grows from short to long across frames
    // tᵢ = totalMs * (i/frames)^2, gap_i = tᵢ - tᵢ₋₁
    const gaps = [];
    let prev = 0;
    for (let i = 1; i <= frames; i++) {
      const t = totalMs * Math.pow(i / frames, 4);
      gaps.push(t - prev);
      prev = t;
    }

    let lastIdx = -1;
    for (let i = 0; i < frames; i++) {
      let idx;
      do {
        idx = Math.floor(Math.random() * pool.length);
      } while (pool.length > 1 && idx === lastIdx);
      lastIdx = idx;
      img.src = pool[idx].src;
      await sleep(gaps[i]);
    }
  }

  function clearResult() {
    slotEl.querySelectorAll("video, audio").forEach((m) => {
      try {
        m.pause();
      } catch (_) {}
      m.removeAttribute("src");
      m.load();
    });
    slotEl.innerHTML = "";
    descriptionEl.textContent = "";
    rarityEl.textContent = "";
    rarityEl.removeAttribute("data-rarity");
  }

  function attachPlayPauseToggle(el) {
    el.addEventListener("click", () => {
      if (el.paused) {
        el.play().catch(() => {});
      } else {
        el.pause();
      }
    });
  }

  function renderResult(item) {
    clearResult();

    let mediaEl;
    if (item.type === "image") {
      mediaEl = document.createElement("img");
      mediaEl.src = item.src;
      mediaEl.alt = item.description || "";
    } else if (item.type === "video") {
      mediaEl = document.createElement("video");
      mediaEl.src = item.src;
      mediaEl.loop = true;
      mediaEl.autoplay = true;
      mediaEl.playsInline = true;
      mediaEl.muted = false;
      attachPlayPauseToggle(mediaEl);
    } else if (item.type === "audio") {
      mediaEl = document.createElement("audio");
      mediaEl.src = item.src;
      mediaEl.loop = true;
      mediaEl.autoplay = true;
      mediaEl.muted = false;
      attachPlayPauseToggle(mediaEl);
    } else if (item.type === "link") {
      mediaEl = document.createElement("a");
      mediaEl.href = item.href;
      mediaEl.target = "_blank";
      mediaEl.rel = "noopener";
      mediaEl.textContent = item.label || item.href;
      mediaEl.className = "lottery-link";
    }

    if (mediaEl) {
      slotEl.appendChild(mediaEl);
      if (mediaEl.tagName === "VIDEO" || mediaEl.tagName === "AUDIO") {
        mediaEl.play().catch(() => {});
      }
    }

    descriptionEl.textContent = item.description || "";
    rarityEl.textContent = item.rarity || "";
    if (item.rarity) {
      rarityEl.setAttribute("data-rarity", item.rarity);
    } else {
      rarityEl.removeAttribute("data-rarity");
    }
  }

  function openLottery() {
    overlay.classList.add("open");
  }

  function closeLottery() {
    overlay.classList.remove("open");
    clearResult();
  }

  let thumbsPreloaded = false;

  function thumbUrl(item) {
    if (item.id !== undefined && item.id !== null) {
      return `lottery_thumbs/${item.id}.jpg`;
    }
    return item.src;
  }

  async function roll() {
    if (rollBtn.disabled) return;
    rollBtn.disabled = true;
    try {
      const data = await loadLotteryData();
      const pick = pickItem(data.items, data.weights);

      const spinPool = data.items
        .filter((it) => it.type === "image" || it.type === "video")
        .map((it) => ({ src: thumbUrl(it) }));

      if (!thumbsPreloaded && spinPool.length > 0) {
        preloadImages(spinPool.map((it) => it.src));
        thumbsPreloaded = true;
      }

      await spinAnimation({ pool: spinPool });
      renderResult(pick);
    } catch (err) {
      clearResult();
      const msg = document.createElement("p");
      msg.textContent = "could not load lottery";
      slotEl.appendChild(msg);
      console.error(err);
    } finally {
      rollBtn.disabled = false;
    }
  }

  openBtn.addEventListener("click", openLottery);
  closeBtn.addEventListener("click", closeLottery);
  rollBtn.addEventListener("click", roll);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.classList.contains("open")) {
      closeLottery();
    }
  });
})();
