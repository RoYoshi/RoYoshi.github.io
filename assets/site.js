/* RoYoshi.github.io: the small things that move.
   Everything here is extra: the page reads the same without it. */
(() => {
  const root = document.documentElement;
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.classList.add("js");

  /* The prompt under the name types what RoYoshi is up to, one line at a time. */
  const cmd = document.querySelector(".prompt__cmd");
  if (cmd && !calm) {
    let lines = [];
    try { lines = JSON.parse(cmd.dataset.lines || "[]"); } catch (_) { /* keep the first line */ }
    let i = 0;
    const wait = (ms) => new Promise((done) => setTimeout(done, ms));
    const loop = async () => {
      for (;;) {
        await wait(2600);
        const text = cmd.textContent;
        for (let n = text.length; n >= 0; n--) { cmd.textContent = text.slice(0, n); await wait(22); }
        i = (i + 1) % lines.length;
        await wait(260);
        for (const ch of lines[i]) { cmd.textContent += ch; await wait(48 + Math.random() * 50); }
      }
    };
    if (lines.length > 1) loop();
  }

  /* Sections rise in as they scroll into view. */
  const parts = document.querySelectorAll(".group, .fetch");
  if (!calm && "IntersectionObserver" in window) {
    const seen = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) { entry.target.classList.add("is-in"); seen.unobserve(entry.target); }
      }
    }, { rootMargin: "0px 0px -8% 0px" });
    parts.forEach((part) => { part.classList.add("rise"); seen.observe(part); });
  }

  /* Tap the hat and he tips it. */
  const hat = document.querySelector(".hero .hat");
  if (hat) {
    hat.addEventListener("click", () => {
      hat.classList.remove("tip");
      void hat.offsetWidth;
      hat.classList.add("tip");
    });
  }

  /* Videos load YouTube's player only when asked to (privacy-enhanced mode). */
  document.querySelectorAll(".video[data-video]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey) return;
      event.preventDefault();
      const frame = document.createElement("iframe");
      frame.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(link.dataset.video)}?autoplay=1&rel=0`;
      frame.title = link.dataset.title || "Video";
      frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      frame.allowFullscreen = true;
      const box = document.createElement("div");
      box.className = "video";
      box.append(frame);
      link.replaceWith(box);
    });
  });

  /* The tape counter in Level 0 runs while you're here. */
  const counter = document.querySelector("[data-timecode]");
  if (counter && !calm) {
    const start = Date.now();
    setInterval(() => {
      const s = Math.floor((Date.now() - start) / 1000);
      counter.textContent = [s / 3600, (s / 60) % 60, s % 60]
        .map((v) => String(Math.floor(v)).padStart(2, "0")).join(":");
    }, 1000);
  }

  /* Type "noclip" anywhere and fall through the page into Level 0. Esc climbs back out. */
  const word = "noclip";
  let typed = "";
  let lights = null;
  const out = () => {
    root.classList.remove("noclipped");
    if (lights) { lights.remove(); lights = null; }
  };
  const fall = () => {
    if (lights) return;
    root.classList.add("noclipped");
    lights = document.createElement("div");
    lights.className = "level0";
    lights.setAttribute("role", "dialog");
    lights.setAttribute("aria-label", "Level 0");
    lights.innerHTML =
      '<div class="level0__card"><p class="level0__title">You noclipped into Level 0.</p>' +
      "<p>Mono-yellow wallpaper, damp carpet, the buzz of the lights. Something is smiling at you from the dark.</p>" +
      '<p class="level0__actions"><a class="cta" href="https://thefarbackrooms.com/">Find the way out</a>' +
      '<button type="button" class="level0__close">Press Esc to wake up</button></p></div>';
    document.body.append(lights);
    lights.querySelector(".level0__close").addEventListener("click", out);
    lights.querySelector(".cta").focus({ preventScroll: true });
  };
  addEventListener("keydown", (event) => {
    if (event.key === "Escape") { out(); return; }
    const target = event.target;
    if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
    if (event.key.length !== 1 || event.ctrlKey || event.metaKey || event.altKey) return;
    typed = (typed + event.key.toLowerCase()).slice(-word.length);
    if (typed === word) { typed = ""; fall(); }
  });
  if (location.hash === "#noclip") fall();

  /* For whoever opens the console. */
  console.log(
    "%c  ▄███▄\n  █████\n▀▀▀▀▀▀▀▀▀%c\nHey, you opened the console. Respect.\nThis site is plain HTML, CSS and a pinch of JS, built by tools/build.py.\nTry typing  noclip  on the page.",
    "color:#00ff00;font-weight:bold", "color:#ff00ff"
  );
})();
