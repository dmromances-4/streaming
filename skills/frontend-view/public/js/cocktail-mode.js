/**
 * Modo Cóctel — overlays de recetas sincronizados con reproducción.
 */
(function () {
  "use strict";

  let cues = [];
  let shown = new Set();
  let toastEl = null;

  function ensureToast() {
    if (toastEl) return toastEl;
    toastEl = document.createElement("div");
    toastEl.id = "cocktail-toast";
    toastEl.className = "cocktail-toast hidden";
    document.body.appendChild(toastEl);
    return toastEl;
  }

  function showCocktail(cocktail) {
    const el = ensureToast();
    const steps = (cocktail.recipe || []).map((s) => `<li>${s}</li>`).join("");
    const ings = (cocktail.ingredients || []).join(" · ");
    el.innerHTML = `
      <button class="cocktail-close" aria-label="Cerrar">×</button>
      <h3>${cocktail.name}</h3>
      <p class="cocktail-scene">${cocktail.scene || ""}</p>
      <p class="cocktail-ingredients">${ings}</p>
      <ol class="cocktail-recipe">${steps}</ol>
    `;
    el.querySelector(".cocktail-close").onclick = () => el.classList.add("hidden");
    el.classList.remove("hidden");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.add("hidden"), 12000);
  }

  function reset() {
    cues = [];
    shown.clear();
    if (toastEl) toastEl.classList.add("hidden");
  }

  function loadCues(cocktailList) {
    reset();
    cues = (cocktailList || [])
      .filter((c) => c.timestamp_seconds != null)
      .sort((a, b) => a.timestamp_seconds - b.timestamp_seconds);
  }

  function onTimeUpdate(video) {
    const t = video.currentTime;
    for (const c of cues) {
      const key = c.id;
      if (shown.has(key)) continue;
      if (t >= c.timestamp_seconds && t < c.timestamp_seconds + 30) {
        shown.add(key);
        showCocktail(c);
      }
    }
  }

  function showManual(cocktail) {
    if (cocktail) showCocktail(cocktail);
  }

  window.CocktailMode = {
    loadCues,
    reset,
    onTimeUpdate,
    showManual,
  };
})();
