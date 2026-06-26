import { useCallback, useState } from "react";
import {
  acquireMovie,
  playMovie,
  resolveManifestUrl,
  titleStatus,
  mapAcquireError,
} from "../api/client";
import { STATUS_LABELS } from "./useEpisodePlay";

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ITERATIONS = 2400;

function pollLabel(status: {
  stage?: string | null;
  pipeline_status: string;
  message?: string | null;
}): string {
  const key = status.stage || status.pipeline_status;
  if (key === "downloading" && status.message) return status.message;
  return STATUS_LABELS[key] || STATUS_LABELS.catalog;
}

async function pollMovieUntilReady(
  titleId: string,
  onTick: (label: string, seconds: number) => void
): Promise<string | null> {
  for (let i = 0; i < POLL_MAX_ITERATIONS; i++) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    const seconds = Math.floor(((i + 1) * POLL_INTERVAL_MS) / 1000);
    const st = await titleStatus(titleId);
    onTick(pollLabel(st), seconds);
    if (st.pipeline_status === "ready" && st.manifest_url) {
      return resolveManifestUrl(st.manifest_url);
    }
    if (st.pipeline_status === "failed") {
      throw new Error(mapAcquireError(st.error_message || st.message || undefined));
    }
  }
  throw new Error(
    "Tiempo de espera agotado. El transcode puede seguir en segundo plano; inténtalo de nuevo en unos minutos."
  );
}

export function useMoviePlay() {
  const [loading, setLoading] = useState(false);
  const [pollStage, setPollStage] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const runPipeline = useCallback(
    async (
      titleId: string,
      start: () => ReturnType<typeof playMovie>
    ): Promise<string | null> => {
      setLoading(true);
      setPollStage(STATUS_LABELS.catalog);
      setElapsedSeconds(0);
      setError(null);
      try {
        const result = await start();
        if (result.pipeline_status === "ready" && result.manifest_url) {
          return resolveManifestUrl(result.manifest_url);
        }
        if (result.pipeline_status === "failed") {
          throw new Error(mapAcquireError(result.message));
        }

        setPollStage(pollLabel(result));

        return await pollMovieUntilReady(titleId, (label, seconds) => {
          setPollStage(label);
          setElapsedSeconds(seconds);
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "No se pudo reproducir la película";
        setError(msg);
        return null;
      } finally {
        setLoading(false);
        setPollStage(null);
        setElapsedSeconds(0);
      }
    },
    []
  );

  const play = useCallback(
    (titleId: string) => runPipeline(titleId, () => playMovie(titleId)),
    [runPipeline]
  );

  const acquire = useCallback(
    (titleId: string) => runPipeline(titleId, () => acquireMovie(titleId)),
    [runPipeline]
  );

  const clearError = useCallback(() => setError(null), []);

  return { play, acquire, loading, pollStage, elapsedSeconds, error, clearError };
}
