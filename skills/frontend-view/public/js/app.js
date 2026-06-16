/**
 * SKILL #4 — Frontend View
 * SPA Vanilla JS + Hls.js + Modo Cóctel + WebTorrent preview
 */
(function () {
  "use strict";

  const API = {
    catalog: "/api/catalog/api/v1",
    ingest: "/api/ingest/api/v1",
    hls: "/api/hls/api/v1",
    live: "/api/live/api/v1",
  };

  const $ = (sel) => document.querySelector(sel);
  const video = $("#video-player");
  const playerStatus = $("#player-status");
  let hlsInstance = null;
  let currentTitleId = null;
  let currentCocktails = [];
  let wtClient = null;
  let currentSeriesId = null;
  let currentSeriesTitle = null;

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      $(`#panel-${tab.dataset.tab}`).classList.add("active");
    });
  });

  function setStatus(el, msg, type) {
    el.textContent = msg;
    el.className = "status" + (type ? " " + type : "");
  }

  function destroyHls() {
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    video.removeAttribute("src");
    video.load();
    window.CocktailMode.reset();
    $("#btn-cocktail-manual").classList.add("hidden");
    currentTitleId = null;
    currentCocktails = [];
  }

  async function loadCocktailsForTitle(titleId) {
    try {
      const list = await apiGet(`${API.catalog}/catalog/${titleId}/cocktails`);
      currentCocktails = list;
      window.CocktailMode.loadCues(list);
      if (list.length) {
        $("#btn-cocktail-manual").classList.remove("hidden");
      }
    } catch (_) {
      window.CocktailMode.reset();
    }
  }

  function playHls(url, titleId) {
    destroyHls();
    setStatus(playerStatus, "Cargando stream…");
    if (titleId) {
      currentTitleId = titleId;
      loadCocktailsForTitle(titleId);
    }

    video.ontimeupdate = () => window.CocktailMode.onTimeUpdate(video);

    if (Hls.isSupported()) {
      hlsInstance = new Hls({ enableWorker: true, lowLatencyMode: true });
      hlsInstance.loadSource(url);
      hlsInstance.attachMedia(video);
      hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        setStatus(playerStatus, "Reproduciendo", "ok");
        video.play().catch(() => {});
      });
      hlsInstance.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) setStatus(playerStatus, "Error HLS: " + data.type, "err");
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = url;
      video.addEventListener("loadedmetadata", () => {
        setStatus(playerStatus, "Reproduciendo (nativo)", "ok");
        video.play().catch(() => {});
      });
    } else {
      setStatus(playerStatus, "HLS no soportado en este navegador", "err");
    }
  }

  async function apiPost(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  async function apiGet(path) {
    const res = await fetch(path);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  async function pollJob(jobId, statusEl) {
    for (let i = 0; i < 120; i++) {
      const st = await apiGet(`${API.hls}/status/${jobId}`);
      setStatus(statusEl, `Job ${jobId}\nEstado: ${st.state} · Segmentos: ${st.segments_count}`);
      if (st.state === "ready") return st;
      if (st.state === "failed") throw new Error(st.error || "Transcode failed");
      await new Promise((r) => setTimeout(r, 3000));
    }
    throw new Error("Timeout esperando transcode");
  }

  async function pollEpisode(episodeId, statusEl) {
    for (let i = 0; i < 240; i++) {
      const st = await apiGet(`${API.catalog}/episodes/${episodeId}/status`);
      const labels = {
        catalog: "Pendiente",
        resolving: "Buscando fuente…",
        ingesting: "Descargando…",
        transcoding: "Transcodificando…",
        ready: "Listo",
        failed: "Fallido",
      };
      setStatus(
        statusEl,
        `Episodio: ${labels[st.pipeline_status] || st.pipeline_status}`
      );
      if (st.pipeline_status === "ready" && st.manifest_url) return st;
      if (st.pipeline_status === "failed") {
        throw new Error(st.error_message || "Pipeline failed");
      }
      await new Promise((r) => setTimeout(r, 3000));
    }
    throw new Error("Timeout esperando episodio");
  }

  function episodeStatusBadge(status) {
    const map = {
      ready: "badge-ready",
      failed: "badge-failed",
      catalog: "badge-pending",
      resolving: "badge-pending",
      ingesting: "badge-pending",
      transcoding: "badge-pending",
    };
    const cls = map[status] || "badge-pending";
    return `<span class="badge ${cls}">${status}</span>`;
  }

  function closeSeriesDetail() {
    $("#series-detail").classList.add("hidden");
    $("#series-detail").setAttribute("aria-hidden", "true");
    currentSeriesId = null;
    currentSeriesTitle = null;
  }

  async function loadEpisodesForSeason(seriesId, season) {
    const listEl = $("#episode-list");
    listEl.innerHTML = "<p class='hint'>Cargando episodios…</p>";
    const episodes = await apiGet(
      `${API.catalog}/catalog/${seriesId}/episodes?season=${season}`
    );
    if (!episodes.length) {
      listEl.innerHTML =
        "<p class='hint'>Sin episodios. Pulsa «Sincronizar episodios (TMDB)».</p>";
      return;
    }
    listEl.innerHTML = "";
    episodes.forEach((ep) => {
      const row = document.createElement("div");
      row.className = "episode-row";
      const runtime = ep.runtime_minutes ? `${ep.runtime_minutes} min` : "";
      const title = ep.title || `Episodio ${ep.episode_number}`;
      let action = "";
      if (ep.pipeline_status === "ready" && ep.manifest_url) {
        action = `<button class="btn btn-sm btn-ep-play" data-id="${ep.id}" data-manifest="${ep.manifest_url}">Reproducir</button>`;
      } else {
        action = `<button class="btn btn-sm primary btn-ep-play" data-id="${ep.id}">Preparar y reproducir</button>`;
      }
      row.innerHTML = `
        <div class="episode-info">
          <strong>S${String(ep.season_number).padStart(2, "0")}E${String(ep.episode_number).padStart(2, "0")}</strong>
          <span>${title}</span>
          <span class="meta">${runtime}</span>
        </div>
        <div class="episode-actions">
          ${episodeStatusBadge(ep.pipeline_status)}
          ${action}
        </div>
      `;
      listEl.appendChild(row);
    });

    listEl.querySelectorAll(".btn-ep-play").forEach((btn) => {
      btn.addEventListener("click", () => playEpisode(btn));
    });
  }

  async function openSeriesDetail(seriesId) {
    currentSeriesId = seriesId;
    const item = await apiGet(`${API.catalog}/catalog/${seriesId}`);
    currentSeriesTitle = item.title;
    const header = $("#series-header");
    const poster = item.poster_url
      ? `<img class="series-poster" src="${item.poster_url}" alt="" />`
      : "";
    header.innerHTML = `
      <div class="series-header-content">
        ${poster}
        <div>
          <h2>${item.title}</h2>
          <p class="meta">${item.origin}${item.year ? ` · ${item.year}` : ""}</p>
          <p class="overview">${item.overview || ""}</p>
        </div>
      </div>
    `;
    $("#series-detail").classList.remove("hidden");
    $("#series-detail").setAttribute("aria-hidden", "false");

    const seasonSelect = $("#season-select");
    seasonSelect.innerHTML = "";
    let seasons = await apiGet(`${API.catalog}/catalog/${seriesId}/seasons`);
    if (!seasons.length) {
      const opt = document.createElement("option");
      opt.value = "1";
      opt.textContent = "Temporada 1";
      seasonSelect.appendChild(opt);
    } else {
      seasons.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = String(s.season_number);
        opt.textContent = `T${s.season_number} (${s.ready_count}/${s.episode_count} listos)`;
        seasonSelect.appendChild(opt);
      });
    }
    await loadEpisodesForSeason(seriesId, seasonSelect.value);
  }

  async function playEpisode(btn) {
    const episodeId = btn.dataset.id;
    const statusEl = $("#series-status");
    btn.disabled = true;
    try {
      if (btn.dataset.manifest) {
        playHls(btn.dataset.manifest, currentSeriesId);
        setStatus(statusEl, "Reproduciendo episodio", "ok");
        return;
      }
      setStatus(statusEl, "Iniciando pipeline del episodio…");
      const play = await apiPost(`${API.catalog}/episodes/${episodeId}/play`, {});
      if (play.pipeline_status === "ready" && play.manifest_url) {
        playHls(play.manifest_url, currentSeriesId);
        setStatus(statusEl, "Reproduciendo", "ok");
        await loadEpisodesForSeason(currentSeriesId, $("#season-select").value);
        return;
      }
      const st = await pollEpisode(episodeId, statusEl);
      playHls(st.manifest_url, currentSeriesId);
      setStatus(statusEl, "Reproduciendo", "ok");
      await loadEpisodesForSeason(currentSeriesId, $("#season-select").value);
    } catch (e) {
      setStatus(statusEl, e.message, "err");
    } finally {
      btn.disabled = false;
    }
  }

  async function loadIngredients() {
    try {
      const data = await apiGet(`${API.catalog}/cocktails/ingredients`);
      const sel = $("#filter-ingredient");
      const current = sel.value;
      sel.innerHTML = '<option value="">Bebida: todas</option>';
      (data.ingredients || []).forEach((ing) => {
        const opt = document.createElement("option");
        opt.value = ing;
        opt.textContent = ing.charAt(0).toUpperCase() + ing.slice(1);
        sel.appendChild(opt);
      });
      sel.value = current;
    } catch (_) {}
  }

  async function loadCatalogStats() {
    try {
      const s = await apiGet(`${API.catalog}/stats`);
      setStatus(
        $("#catalog-stats"),
        `Total: ${s.total} · Coctelería: ${s.cocteleria} · Listos: ${s.ready} · Magnets: ${s.magnets_resolved}`,
        "ok"
      );
    } catch (e) {
      setStatus($("#catalog-stats"), e.message, "err");
    }
  }

  async function loadCatalog() {
    const params = new URLSearchParams({ limit: "100" });
    const type = $("#filter-type").value;
    const origin = $("#filter-origin").value;
    const status = $("#filter-status").value;
    const ingredient = $("#filter-ingredient").value;
    if (type) params.set("type", type);
    if (origin) params.set("origin", origin);
    if (status) params.set("status", status);
    if (ingredient) params.set("ingredient", ingredient);
    if ($("#filter-cocteleria").checked) params.set("cocteleria", "1");

    try {
      const data = await apiGet(`${API.catalog}/catalog?${params}`);
      const grid = $("#catalog-grid");
      grid.innerHTML = "";

      data.items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "catalog-card";
        const badges = [];
        if (item.tags && item.tags.includes("cocteleria")) {
          badges.push('<span class="badge badge-cocteleria">COCTELERÍA</span>');
        }
        if (item.pipeline_status === "ready") {
          badges.push('<span class="badge badge-ready">LISTO</span>');
        } else if (item.pipeline_status === "failed") {
          badges.push('<span class="badge badge-failed">FALLIDO</span>');
        } else {
          badges.push('<span class="badge badge-pending">' + item.pipeline_status + "</span>");
        }

        const poster = item.poster_url
          ? `<img class="poster" src="${item.poster_url}" alt="" loading="lazy" />`
          : "";
        const overview = item.overview
          ? `<p class="overview">${item.overview}</p>`
          : "";
        const year = item.year ? ` · ${item.year}` : "";

        let actionBtn = "";
        if (item.content_type === "series") {
          actionBtn = `<button class="btn-series" data-id="${item.id}">Ver episodios</button>`;
        } else if (item.manifest_url) {
          actionBtn = `<button class="btn-play" data-manifest="${item.manifest_url}" data-id="${item.id}">Reproducir</button>`;
        }

        card.innerHTML = `
          ${poster}
          <h3>${item.title}</h3>
          <div class="meta">${item.content_type}${year} · ${item.origin}</div>
          ${overview}
          <div>${badges.join("")}</div>
          ${actionBtn}
        `;
        grid.appendChild(card);
      });

      grid.querySelectorAll(".btn-play").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          playHls(btn.dataset.manifest, btn.dataset.id);
        });
      });

      grid.querySelectorAll(".btn-series").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          openSeriesDetail(btn.dataset.id).catch((err) =>
            setStatus($("#catalog-stats"), err.message, "err")
          );
        });
      });

      grid.querySelectorAll(".catalog-card").forEach((card, i) => {
        const item = data.items[i];
        if (item.content_type === "series") {
          card.style.cursor = "pointer";
          card.addEventListener("click", () =>
            openSeriesDetail(item.id).catch((err) =>
              setStatus($("#catalog-stats"), err.message, "err")
            )
          );
        }
      });

      await loadCatalogStats();
    } catch (e) {
      setStatus($("#catalog-stats"), e.message, "err");
    }
  }

  $("#filter-type").addEventListener("change", loadCatalog);
  $("#filter-origin").addEventListener("change", loadCatalog);
  $("#filter-status").addEventListener("change", loadCatalog);
  $("#filter-cocteleria").addEventListener("change", loadCatalog);
  $("#filter-ingredient").addEventListener("change", loadCatalog);

  $("#btn-import").addEventListener("click", async () => {
    try {
      const r = await apiPost(`${API.catalog}/import`, { source: "seed" });
      setStatus($("#catalog-stats"), `Importados: ${r.inserted} · Duplicados: ${r.skipped_duplicates}`, "ok");
      await loadIngredients();
      loadCatalog();
    } catch (e) {
      setStatus($("#catalog-stats"), e.message, "err");
    }
  });

  $("#btn-enrich").addEventListener("click", async () => {
    $("#btn-enrich").disabled = true;
    try {
      const r = await apiPost(`${API.catalog}/enrich-metadata`, { priority_only: true, limit: 50 });
      setStatus($("#catalog-stats"), `TMDB OK: ${r.resolved} · Fallos: ${r.failed}`, "ok");
      loadCatalog();
    } catch (e) {
      setStatus($("#catalog-stats"), e.message, "err");
    } finally {
      $("#btn-enrich").disabled = false;
    }
  });

  $("#btn-resolve").addEventListener("click", async () => {
    $("#btn-resolve").disabled = true;
    try {
      const r = await apiPost(`${API.catalog}/resolve-magnets`, { priority_only: true, limit: 42 });
      setStatus($("#catalog-stats"), `Resueltos: ${r.resolved} · Fallidos: ${r.failed}`, "ok");
      loadCatalog();
    } catch (e) {
      setStatus($("#catalog-stats"), e.message, "err");
    } finally {
      $("#btn-resolve").disabled = false;
    }
  });

  $("#btn-batch-ingest").addEventListener("click", async () => {
    $("#btn-batch-ingest").disabled = true;
    setStatus($("#catalog-stats"), "Ingesta batch en curso (puede tardar)…");
    try {
      const r = await apiPost(`${API.catalog}/batch-ingest`, {
        priority_only: true,
        limit: 5,
        concurrency: 2,
      });
      setStatus($("#catalog-stats"), `OK: ${r.success} · Fallos: ${r.failed}`, r.failed ? "err" : "ok");
      loadCatalog();
    } catch (e) {
      setStatus($("#catalog-stats"), e.message, "err");
    } finally {
      $("#btn-batch-ingest").disabled = false;
    }
  });

  $("#btn-cocktail-manual").addEventListener("click", () => {
    if (currentCocktails.length) {
      window.CocktailMode.showManual(currentCocktails[0]);
    }
  });

  $("#btn-ingest").addEventListener("click", async () => {
    const magnet = $("#magnet-input").value.trim();
    const statusEl = $("#torrent-status");
    const btn = $("#btn-ingest");
    if (!magnet.startsWith("magnet:?")) {
      setStatus(statusEl, "Magnet URI inválida", "err");
      return;
    }
    btn.disabled = true;
    try {
      setStatus(statusEl, "Ingestando torrent…");
      const ing = await apiPost(`${API.ingest}/ingest`, { magnet_uri: magnet });
      const job = await apiPost(`${API.hls}/transcode`, { session_id: ing.session_id });
      await pollJob(job.job_id, statusEl);
      playHls(`${API.hls}/manifest/${job.job_id}`);
      setStatus(statusEl, `Listo · Job ${job.job_id}`, "ok");
    } catch (err) {
      setStatus(statusEl, err.message, "err");
    } finally {
      btn.disabled = false;
    }
  });

  $("#btn-p2p-play").addEventListener("click", () => {
    const magnet = $("#p2p-magnet-input").value.trim();
    const statusEl = $("#p2p-status");
    if (!magnet.startsWith("magnet:?")) {
      setStatus(statusEl, "Magnet URI inválida", "err");
      return;
    }
    if (typeof WebTorrent === "undefined") {
      setStatus(statusEl, "WebTorrent no cargado", "err");
      return;
    }
    destroyHls();
    if (wtClient) wtClient.destroy();
    wtClient = new WebTorrent();
    setStatus(statusEl, "Conectando peers P2P…");
    wtClient.add(magnet, (torrent) => {
      const file = torrent.files.find((f) =>
        /\.(mp4|mkv|webm|avi)$/i.test(f.name)
      );
      if (!file) {
        setStatus(statusEl, "No se encontró archivo de video en el torrent", "err");
        return;
      }
      file.renderTo(video, { autoplay: true }, (err) => {
        if (err) setStatus(statusEl, err.message, "err");
        else setStatus(statusEl, `P2P: ${file.name}`, "ok");
      });
    });
  });

  $("#btn-live-play").addEventListener("click", () => {
    const url = $("#live-url-input").value.trim();
    if (!url.startsWith("http")) {
      setStatus(playerStatus, "URL inválida", "err");
      return;
    }
    playHls(`${API.live}/proxy?url=${encodeURIComponent(url)}`);
  });

  $("#btn-hls-play").addEventListener("click", () => {
    const jobId = $("#job-id-input").value.trim();
    if (!jobId) {
      setStatus(playerStatus, "Introduce un job_id", "err");
      return;
    }
    playHls(`${API.hls}/manifest/${jobId}`);
  });

  $("#btn-series-close").addEventListener("click", closeSeriesDetail);

  $("#season-select").addEventListener("change", () => {
    if (currentSeriesId) {
      loadEpisodesForSeason(currentSeriesId, $("#season-select").value).catch((e) =>
        setStatus($("#series-status"), e.message, "err")
      );
    }
  });

  $("#btn-sync-episodes").addEventListener("click", async () => {
    if (!currentSeriesId) return;
    const btn = $("#btn-sync-episodes");
    btn.disabled = true;
    try {
      const r = await apiPost(
        `${API.catalog}/catalog/${currentSeriesId}/sync-episodes`,
        {}
      );
      setStatus(
        $("#series-status"),
        `Episodios: +${r.inserted || 0} nuevos · ${r.updated || 0} actualizados`,
        "ok"
      );
      await openSeriesDetail(currentSeriesId);
    } catch (e) {
      setStatus($("#series-status"), e.message, "err");
    } finally {
      btn.disabled = false;
    }
  });

  $("#btn-resolve-season").addEventListener("click", async () => {
    if (!currentSeriesId) return;
    const btn = $("#btn-resolve-season");
    btn.disabled = true;
    try {
      const season = parseInt($("#season-select").value, 10);
      const r = await apiPost(
        `${API.catalog}/catalog/${currentSeriesId}/resolve-episodes`,
        { season_number: season, limit: 42 }
      );
      setStatus(
        $("#series-status"),
        `Magnets: ${r.resolved || 0} OK · ${r.failed || 0} fallos`,
        r.failed ? "err" : "ok"
      );
      await loadEpisodesForSeason(currentSeriesId, season);
    } catch (e) {
      setStatus($("#series-status"), e.message, "err");
    } finally {
      btn.disabled = false;
    }
  });

  loadIngredients();
  loadCatalog();
})();
