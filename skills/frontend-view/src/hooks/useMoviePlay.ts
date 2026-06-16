import { useCallback, useState } from "react";
import { playMovie, resolveManifestUrl, titleStatus } from "../api/client";
import { STATUS_LABELS } from "./useEpisodePlay";

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ITERATIONS = 2400;

export function useMoviePlay() {
  const [loading, setLoading] = useState(false);
  const [pollStage, setPollStage] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const play = useCallback(async (titleId: string): Promise<string | null> => {
    setLoading(true);
    setPollStage("catalog");
    setElapsedSeconds(0);
    setError(null);
    try {
      const result = await playMovie(titleId);
      if (result.pipeline_status === "ready" && result.manifest_url) {
        return resolveManifestUrl(result.manifest_url);
      }
      if (result.pipeline_status === "failed") {
        throw new Error(result.message || "No se pudo preparar la película");
      }

      setPollStage(STATUS_LABELS[result.pipeline_status] || "Transcodificando…");

      for (let i = 0; i < POLL_MAX_ITERATIONS; i++) {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        const seconds = Math.floor(((i + 1) * POLL_INTERVAL_MS) / 1000);
        setElapsedSeconds(seconds);
        const st = await titleStatus(titleId);
        const label = STATUS_LABELS[st.pipeline_status] || st.pipeline_status;
        setPollStage(label);
        if (st.pipeline_status === "ready" && st.manifest_url) {
          return resolveManifestUrl(st.manifest_url);
        }
        if (st.pipeline_status === "failed") {
          throw new Error(st.error_message || "No se pudo preparar la película");
        }
      }
      throw new Error(
        "Tiempo de espera agotado. El transcode puede seguir en segundo plano; inténtalo de nuevo en unos minutos."
      );
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "No se pudo reproducir la película";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
      setPollStage(null);
      setElapsedSeconds(0);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { play, loading, pollStage, elapsedSeconds, error, clearError };
}
