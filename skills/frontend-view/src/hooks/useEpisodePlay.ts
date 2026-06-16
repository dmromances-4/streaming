import { useCallback, useState } from "react";
import {
  acquireEpisode,
  episodeStatus,
  mapAcquireError,
  playEpisode,
  resolveManifestUrl,
} from "../api/client";
import type { EpisodePlayResponse } from "../api/types";

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ITERATIONS = 2400;

export const STATUS_LABELS: Record<string, string> = {
  catalog: "Preparando…",
  resolving: "Buscando torrent…",
  searching: "Buscando torrent…",
  ingesting: "Descargando…",
  downloading: "Descargando…",
  transcoding: "Transcodificando…",
  ready: "Listo",
  failed: "Error",
};

function pollLabel(status: {
  stage?: string | null;
  pipeline_status: string;
  message?: string | null;
  download_progress?: number | null;
  download_speed_mbps?: number | null;
}): { key: string; label: string } {
  const key = status.stage || status.pipeline_status;
  if (key === "downloading") {
    if (status.download_progress != null && status.download_progress > 0) {
      const speed =
        status.download_speed_mbps != null && status.download_speed_mbps > 0
          ? ` · ${status.download_speed_mbps.toFixed(1)} MB/s`
          : "";
      return {
        key,
        label: `Descargando… ${status.download_progress.toFixed(0)}%${speed}`,
      };
    }
    if (status.message) return { key, label: status.message };
  }
  return { key, label: STATUS_LABELS[key] || STATUS_LABELS.catalog };
}

async function pollUntilReady(
  episodeId: string,
  onTick: (key: string, label: string, seconds: number) => void,
  onComplete?: () => void
): Promise<string | null> {
  for (let i = 0; i < POLL_MAX_ITERATIONS; i++) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    const seconds = Math.floor(((i + 1) * POLL_INTERVAL_MS) / 1000);
    const st = await episodeStatus(episodeId);
    const { key, label } = pollLabel(st);
    onTick(key, label, seconds);
    if (st.pipeline_status === "ready" && st.manifest_url) {
      onComplete?.();
      return resolveManifestUrl(st.manifest_url);
    }
    if (st.pipeline_status === "failed") {
      throw new Error(
        mapAcquireError(st.error_message || st.message || undefined)
      );
    }
  }
  throw new Error(
    "Tiempo de espera agotado. El transcode puede seguir en segundo plano; inténtalo de nuevo en unos minutos."
  );
}

export function useEpisodePlay() {
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [pollStage, setPollStage] = useState<string | null>(null);
  const [pollStageKey, setPollStageKey] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [errorEpisodeId, setErrorEpisodeId] = useState<string | null>(null);

  const runPipeline = useCallback(
    async (
      episodeId: string,
      start: () => Promise<EpisodePlayResponse>,
      onComplete?: () => void
    ): Promise<string | null> => {
      setLoadingId(episodeId);
      setPollStageKey("catalog");
      setPollStage(STATUS_LABELS.catalog);
      setElapsedSeconds(0);
      setError(null);
      setErrorEpisodeId(null);
      try {
        const result = await start();
        if (result.pipeline_status === "ready" && result.manifest_url) {
          onComplete?.();
          return resolveManifestUrl(result.manifest_url);
        }
        if (result.pipeline_status === "failed") {
          throw new Error(mapAcquireError(result.message));
        }

        const initial = pollLabel(result);
        setPollStageKey(initial.key);
        setPollStage(initial.label);

        return await pollUntilReady(
          episodeId,
          (key, label, seconds) => {
            setPollStageKey(key);
            setPollStage(label);
            setElapsedSeconds(seconds);
          },
          onComplete
        );
      } catch (e) {
        const msg =
          e instanceof Error
            ? e.message
            : "No se pudo reproducir el episodio";
        setError(msg);
        setErrorEpisodeId(episodeId);
        onComplete?.();
        return null;
      } finally {
        setLoadingId(null);
        setPollStage(null);
        setPollStageKey(null);
        setElapsedSeconds(0);
      }
    },
    []
  );

  const play = useCallback(
    (episodeId: string, onComplete?: () => void) =>
      runPipeline(episodeId, () => playEpisode(episodeId), onComplete),
    [runPipeline]
  );

  const acquire = useCallback(
    (episodeId: string, onComplete?: () => void) =>
      runPipeline(episodeId, () => acquireEpisode(episodeId), onComplete),
    [runPipeline]
  );

  const clearError = useCallback(() => {
    setError(null);
    setErrorEpisodeId(null);
  }, []);

  return {
    play,
    acquire,
    loadingId,
    pollStage,
    pollStageKey,
    elapsedSeconds,
    error,
    errorEpisodeId,
    clearError,
    statusLabels: STATUS_LABELS,
  };
}
