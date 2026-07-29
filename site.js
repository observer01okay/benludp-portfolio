async function sha256(text) {
  const data = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Strip Facebook/Google tracking junk (?fbclid=, ?utm_…) from the address bar */
function stripTrackingParams() {
  const url = new URL(window.location.href);
  if (![...url.searchParams.keys()].length) return;

  const drop = new Set([
    "fbclid",
    "gclid",
    "gbraid",
    "wbraid",
    "mc_eid",
    "igshid",
    "twclid",
  ]);
  let changed = false;
  for (const key of [...url.searchParams.keys()]) {
    if (drop.has(key) || key.startsWith("utm_")) {
      url.searchParams.delete(key);
      changed = true;
    }
  }
  if (!changed) return;

  const clean = url.pathname + (url.search ? url.search : "") + url.hash;
  history.replaceState(null, "", clean || "/");
}

function initPasswordGates() {
  document.querySelectorAll(".password-gate").forEach((gate) => {
    const form = gate.querySelector(".password-form");
    const content = gate.querySelector(".password-content");
    const error = gate.querySelector(".password-error");
    const expected = gate.dataset.hash;
    const slug = gate.dataset.slug || "project";
    const key = `benlu-unlock:${slug}`;

    async function unlock() {
      form.hidden = true;
      content.hidden = false;
      gate.classList.add("is-unlocked");
      sessionStorage.setItem(key, "1");
    }

    if (sessionStorage.getItem(key) === "1") {
      unlock();
      return;
    }

    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const value = new FormData(form).get("password")?.toString() || "";
      const hash = await sha256(value);
      if (hash === expected) {
        error.hidden = true;
        unlock();
      } else {
        error.hidden = false;
      }
    });
  });
}

/** Adobe-style lightbox for gallery / stills / project images */
function initLightbox() {
  const selectors = [
    ".project-grid img",
    ".project-gallery img",
    ".stills-stack img",
    ".info-portrait",
  ].join(", ");

  const sources = [...document.querySelectorAll(selectors)].filter((img) => img.getAttribute("src"));
  if (!sources.length) return;

  sources.forEach((img, i) => {
    img.classList.add("lb-trigger");
    img.dataset.lbIndex = String(i);
    img.setAttribute("tabindex", "0");
    img.setAttribute("role", "button");
    img.setAttribute("aria-label", "View larger image");
  });

  const root = document.createElement("div");
  root.className = "lightbox";
  root.hidden = true;
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-modal", "true");
  root.setAttribute("aria-label", "Image viewer");
  root.innerHTML = `
    <button type="button" class="lightbox-close" aria-label="Close">×</button>
    <button type="button" class="lightbox-nav lightbox-prev" aria-label="Previous">‹</button>
    <button type="button" class="lightbox-nav lightbox-next" aria-label="Next">›</button>
    <div class="lightbox-stage">
      <img class="lightbox-image" alt="" />
    </div>
    <div class="lightbox-thumbs" role="list"></div>
  `;
  document.body.appendChild(root);

  const stageImg = root.querySelector(".lightbox-image");
  const thumbs = root.querySelector(".lightbox-thumbs");
  const btnClose = root.querySelector(".lightbox-close");
  const btnPrev = root.querySelector(".lightbox-prev");
  const btnNext = root.querySelector(".lightbox-next");

  sources.forEach((img, i) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lightbox-thumb";
    btn.setAttribute("role", "listitem");
    btn.setAttribute("aria-label", `Image ${i + 1}`);
    btn.dataset.lbIndex = String(i);
    const thumb = document.createElement("img");
    thumb.src = img.currentSrc || img.src;
    thumb.alt = "";
    thumb.loading = "lazy";
    btn.appendChild(thumb);
    thumbs.appendChild(btn);
  });

  let index = 0;
  let open = false;

  function show(i) {
    index = (i + sources.length) % sources.length;
    const src = sources[index];
    stageImg.src = src.currentSrc || src.src;
    const thumbBtns = [...thumbs.querySelectorAll(".lightbox-thumb")];
    thumbBtns.forEach((t, ti) => t.classList.toggle("is-active", ti === index));
    const active = thumbBtns[index];
    // Pin active thumb to the leftmost edge of the strip so it never scrolls out of frame
    if (active) {
      const leftPad = parseFloat(getComputedStyle(thumbs).paddingLeft) || 0;
      thumbs.scrollTo({
        left: Math.max(0, active.offsetLeft - leftPad),
        behavior: "smooth",
      });
    }
    btnPrev.hidden = sources.length < 2;
    btnNext.hidden = sources.length < 2;
  }

  function openAt(i) {
    open = true;
    root.hidden = false;
    document.body.classList.add("lightbox-open");
    show(i);
    btnClose.focus({ preventScroll: true });
  }

  function close() {
    open = false;
    root.hidden = true;
    document.body.classList.remove("lightbox-open");
    stageImg.removeAttribute("src");
  }

  function onTrigger(e) {
    const img = e.target.closest(selectors);
    if (!img || !sources.includes(img)) return;
    e.preventDefault();
    openAt(Number(img.dataset.lbIndex) || 0);
  }

  document.addEventListener("click", onTrigger);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.classList?.contains("lb-trigger")) {
      e.preventDefault();
      openAt(Number(e.target.dataset.lbIndex) || 0);
      return;
    }
    if (!open) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(index - 1);
    if (e.key === "ArrowRight") show(index + 1);
  });

  btnClose.addEventListener("click", close);
  btnPrev.addEventListener("click", () => show(index - 1));
  btnNext.addEventListener("click", () => show(index + 1));
  thumbs.addEventListener("click", (e) => {
    const t = e.target.closest(".lightbox-thumb");
    if (!t) return;
    show(Number(t.dataset.lbIndex) || 0);
  });
  root.addEventListener("click", (e) => {
    if (e.target === root || e.target.classList.contains("lightbox-stage")) close();
  });
}

stripTrackingParams();
initPasswordGates();
initLightbox();
initLocalVideos();

/** Custom play overlay for self-hosted <video> (cleaner than bare controls-on-poster) */
function initLocalVideos() {
  document.querySelectorAll(".local-video-shell").forEach((shell) => {
    const video = shell.querySelector("video");
    const btn = shell.querySelector(".local-video-play");
    if (!video || !btn) return;

    function play() {
      shell.classList.add("is-playing");
      video.setAttribute("controls", "");
      video.play().catch(() => {
        shell.classList.remove("is-playing");
        video.removeAttribute("controls");
      });
    }

    function reset() {
      shell.classList.remove("is-playing");
      video.removeAttribute("controls");
      video.pause();
      video.currentTime = 0;
    }

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      play();
    });

    video.addEventListener("ended", reset);
    video.addEventListener("pause", () => {
      // Keep controls while paused mid-play; only restore poster UI at end/reset
      if (video.currentTime > 0.05 && !video.ended) return;
      if (!video.ended) return;
      reset();
    });
  });
}

