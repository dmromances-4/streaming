import type {
  ActiveDownloadsResponse,
  CatalogItem,
  CatalogListResponse,
  CatalogStats,
  CocktailItem,
  EpisodeItem,
  EpisodeListResponse,
  EpisodeAcquireResponse,
  EpisodePlayResponse,
  EpisodeStatusResponse,
  LiveAuthStatus,
  LiveChannelListResponse,
  LiveStreamResponse,
  SeasonSummary,
  SystemStatus,
  TitlePlayResponse,
  TitleStatusResponse,
  TmdbSearchResponse,
  TitleAcquireResponse,
} from "./types";

const CATALOG = "/api/catalog/api/v1";
const LIVE = "/api/live/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      (data as { error?: string }).error || res.statusText || "Request failed"
    );
  }
  return data as T;
}

export interface CatalogQuery {
  type?: string;
  origin?: string;
  cocteleria?: boolean;
  status?: string;
  q?: string;
  ingredient?: string;
  genre?: string;
  withoutLocal?: boolean;
  limit?: number;
  offset?: number;
}

export function fetchSystemStatus(): Promise<SystemStatus> {
  return request(`${CATALOG}/system/status`);
}

export function fetchStats(): Promise<CatalogStats> {
  return request(`${CATALOG}/stats`);
}

export function fetchActiveDownloads(): Promise<ActiveDownloadsResponse> {
  return request(`${CATALOG}/downloads/active`);
}

export function fetchSimilarTitles(titleId: string): Promise<CatalogListResponse> {
  return request(`${CATALOG}/catalog/${titleId}/similar`);
}

export function fetchLocalLibrary(limit = 20): Promise<CatalogListResponse> {
  return request(`${CATALOG}/catalog/local-library?limit=${limit}`);
}

export function fetchCatalog(query: CatalogQuery = {}): Promise<CatalogListResponse> {
  const params = new URLSearchParams();
  if (query.type) params.set("type", query.type);
  if (query.origin) params.set("origin", query.origin);
  if (query.cocteleria) params.set("cocteleria", "1");
  if (query.status) params.set("status", query.status);
  if (query.q) params.set("q", query.q);
  if (query.ingredient) params.set("ingredient", query.ingredient);
  if (query.genre) params.set("genre", query.genre);
  if (query.withoutLocal) params.set("without_local", "1");
  params.set("limit", String(query.limit ?? 50));
  params.set("offset", String(query.offset ?? 0));
  return request(`${CATALOG}/catalog?${params}`);
}

export function fetchTitle(id: string): Promise<CatalogItem> {
  return request(`${CATALOG}/catalog/${id}`);
}

export function fetchSeasons(seriesId: string): Promise<SeasonSummary[]> {
  return request(`${CATALOG}/catalog/${seriesId}/seasons`);
}

export function fetchEpisodes(
  seriesId: string,
  season: number
): Promise<EpisodeListResponse> {
  return request(`${CATALOG}/catalog/${seriesId}/episodes?season=${season}`);
}

export function fetchEpisode(episodeId: string): Promise<EpisodeItem> {
  return request(`${CATALOG}/episodes/${episodeId}`);
}

export function ensureEpisodes(seriesId: string): Promise<unknown> {
  return request(`${CATALOG}/catalog/${seriesId}/ensure-episodes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function playEpisode(episodeId: string): Promise<EpisodePlayResponse> {
  return request(`${CATALOG}/episodes/${episodeId}/play`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function acquireEpisode(episodeId: string): Promise<EpisodeAcquireResponse> {
  return request(`${CATALOG}/episodes/${episodeId}/acquire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function playMovie(titleId: string): Promise<TitlePlayResponse> {
  return request(`${CATALOG}/catalog/${titleId}/play`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function acquireMovie(titleId: string): Promise<TitleAcquireResponse> {
  return request(`${CATALOG}/catalog/${titleId}/acquire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function searchTmdb(
  q: string,
  type?: "movie" | "series"
): Promise<TmdbSearchResponse> {
  const params = new URLSearchParams({ q });
  if (type) params.set("type", type);
  return request(`${CATALOG}/search/tmdb?${params}`);
}

export function requestTitle(
  tmdbId: number,
  contentType: "movie" | "series"
): Promise<CatalogItem> {
  return request(`${CATALOG}/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tmdb_id: tmdbId, content_type: contentType }),
  });
}

export function requestSeason(
  seriesId: string,
  season: number
): Promise<{ processed: number; success?: number; failed?: number }> {
  return request(`${CATALOG}/catalog/${seriesId}/request-season?season=${season}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function titleStatus(titleId: string): Promise<TitleStatusResponse> {
  return request(`${CATALOG}/catalog/${titleId}/status`);
}

export function scanSeriesLibrary(seriesId: string): Promise<{ processed: number; resolved?: number }> {
  return request(`${CATALOG}/catalog/${seriesId}/scan-library`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function fetchTopGenres(limit = 6): Promise<{ genres: string[] }> {
  return request(`${CATALOG}/catalog/genres/top?limit=${limit}`);
}

export function scanMovieLibrary(titleId: string): Promise<{ processed: number; resolved?: number }> {
  return request(`${CATALOG}/catalog/${titleId}/scan-movie`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function scanAllLibrary(): Promise<{ processed: number; resolved?: number }> {
  return request(`${CATALOG}/catalog/scan-all-library`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function episodeStatus(episodeId: string): Promise<EpisodeStatusResponse> {
  return request(`${CATALOG}/episodes/${episodeId}/status`);
}

export function fetchCocktails(titleId: string): Promise<CocktailItem[]> {
  return request(`${CATALOG}/catalog/${titleId}/cocktails`);
}

export interface LiveChannelQuery {
  country?: string;
  q?: string;
  tag?: string;
}

export function fetchLiveChannels(
  query: LiveChannelQuery = {}
): Promise<LiveChannelListResponse> {
  const params = new URLSearchParams();
  if (query.country) params.set("country", query.country);
  if (query.q) params.set("q", query.q);
  if (query.tag) params.set("tag", query.tag);
  const qs = params.toString();
  return request(`${LIVE}/channels${qs ? `?${qs}` : ""}`);
}

export function fetchLiveChannelStream(channelId: string): Promise<LiveStreamResponse> {
  return request(`${LIVE}/channels/${channelId}/stream`);
}

export function fetchLiveAuthStatus(): Promise<LiveAuthStatus> {
  return request(`${LIVE}/auth/status`);
}

export function resolveManifestUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("/")) return url;
  try {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return url;
  }
}

export function mapAcquireError(raw: string | null | undefined): string {
  if (!raw) return "No se pudo preparar el episodio.";
  const lower = raw.toLowerCase();
  if (lower.includes("indexer") || lower.includes("prowlarr")) {
    return "Configura Prowlarr y INDEXER_API_KEY en Ajustes.";
  }
  if (lower.includes("no matching") || lower.includes("no se encontró torrent")) {
    return "No hay torrent adecuado. Prueba más tarde o revisa los indexers.";
  }
  if (lower.includes("qbittorrent")) {
    return "Revisa qBittorrent en http://localhost:8080";
  }
  if (lower.includes("timeout")) {
    return "La descarga tardó demasiado. Comprueba qBittorrent.";
  }
  return raw;
}
