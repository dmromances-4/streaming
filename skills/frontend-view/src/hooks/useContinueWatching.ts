import { useCallback, useEffect, useState } from "react";
import { fetchEpisode, fetchTitle } from "../api/client";
import type { CatalogItem } from "../api/types";

const WATCH_PREFIX = "watch:";

export interface ContinueItem {
  id: string;
  title: string;
  poster_url?: string | null;
  progressPercent: number;
  href: string;
  kind: "episode" | "movie";
}

interface WatchMeta {
  position: number;
  duration: number;
  updatedAt: number;
  kind?: "episode" | "movie";
}

function readWatchEntries(): { key: string; meta: WatchMeta }[] {
  const entries: { key: string; meta: WatchMeta }[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key?.startsWith(WATCH_PREFIX)) continue;
    const raw = localStorage.getItem(key);
    if (!raw) continue;
    try {
      const parsed = JSON.parse(raw) as WatchMeta;
      if (parsed.updatedAt && parsed.duration > 0) {
        entries.push({ key, meta: parsed });
      }
    } catch {
      const position = Number(raw);
      if (position > 30) {
        entries.push({
          key,
          meta: { position, duration: 0, updatedAt: Date.now() },
        });
      }
    }
  }
  return entries.sort((a, b) => b.meta.updatedAt - a.meta.updatedAt);
}

export function useContinueWatching(limit = 12) {
  const [items, setItems] = useState<ContinueItem[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    const entries = readWatchEntries().slice(0, limit);
    const resolved: ContinueItem[] = [];

    for (const { key, meta } of entries) {
      const id = key.slice(WATCH_PREFIX.length);
      try {
        const isMovie = meta.kind === "movie" || id.startsWith("movie-");
        if (isMovie) {
          const t = await fetchTitle(id);
          const pct =
            meta.duration > 0
              ? Math.min(99, Math.round((meta.position / meta.duration) * 100))
              : 0;
          resolved.push({
            id,
            title: t.title,
            poster_url: t.poster_url,
            progressPercent: pct,
            href: `/watch/movie/${id}`,
            kind: "movie",
          });
        } else {
          const ep = await fetchEpisode(id);
          const series = await fetchTitle(ep.series_id);
          const pct =
            meta.duration > 0
              ? Math.min(99, Math.round((meta.position / meta.duration) * 100))
              : 0;
          resolved.push({
            id,
            title: `${series.title} S${ep.season_number}E${ep.episode_number}`,
            poster_url: ep.still_url || series.poster_url,
            progressPercent: pct,
            href: `/watch/${id}`,
            kind: "episode",
          });
        }
      } catch {
        // skip stale entries
      }
    }
    setItems(resolved);
    setLoading(false);
  }, [limit]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { items, loading, reload };
}
