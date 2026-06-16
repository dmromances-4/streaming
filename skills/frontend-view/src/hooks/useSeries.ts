import { useCallback, useEffect, useState } from "react";
import {
  ensureEpisodes,
  fetchEpisodes,
  fetchSeasons,
  fetchTitle,
  scanSeriesLibrary,
} from "../api/client";
import type { CatalogItem, EpisodeItem, SeasonSummary } from "../api/types";

export function useSeries(seriesId: string | undefined) {
  const [title, setTitle] = useState<CatalogItem | null>(null);
  const [seasons, setSeasons] = useState<SeasonSummary[]>([]);
  const [episodes, setEpisodes] = useState<EpisodeItem[]>([]);
  const [activeSeason, setActiveSeason] = useState(1);
  const [loading, setLoading] = useState(true);
  const [episodesLoading, setEpisodesLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEpisodes = useCallback(
    async (season: number) => {
      if (!seriesId) return;
      setEpisodesLoading(true);
      try {
        const res = await fetchEpisodes(seriesId, season);
        setEpisodes(res.items);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error al cargar episodios");
      } finally {
        setEpisodesLoading(false);
      }
    },
    [seriesId]
  );

  const reloadSeasons = useCallback(async () => {
    if (!seriesId) return;
    const s = await fetchSeasons(seriesId);
    setSeasons(s);
    return s;
  }, [seriesId]);

  useEffect(() => {
    if (!seriesId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const t = await fetchTitle(seriesId!);
        if (cancelled) return;
        setTitle(t);

        if (t.content_type === "series") {
          await ensureEpisodes(seriesId!);
          if (cancelled) return;

          setScanning(true);
          try {
            await scanSeriesLibrary(seriesId!);
          } catch {
            // scan is best-effort when opening a series
          } finally {
            if (!cancelled) setScanning(false);
          }

          const s = await fetchSeasons(seriesId!);
          if (cancelled) return;
          setSeasons(s);
          const first = s[0]?.season_number ?? 1;
          setActiveSeason(first);
          const eps = await fetchEpisodes(seriesId!, first);
          if (!cancelled) setEpisodes(eps.items);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error al cargar serie");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [seriesId]);

  useEffect(() => {
    if (!seriesId || loading) return;
    loadEpisodes(activeSeason);
  }, [activeSeason, seriesId, loading, loadEpisodes]);

  const reloadEpisodes = useCallback(async () => {
    await reloadSeasons();
    await loadEpisodes(activeSeason);
  }, [activeSeason, loadEpisodes, reloadSeasons]);

  return {
    title,
    seasons,
    episodes,
    activeSeason,
    setActiveSeason,
    loading,
    episodesLoading,
    scanning,
    error,
    reloadEpisodes,
  };
}
