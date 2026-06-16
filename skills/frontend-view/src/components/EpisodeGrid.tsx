import { useNavigate } from "react-router-dom";
import type { EpisodeItem } from "../api/types";
import { useEpisodePlay } from "../hooks/useEpisodePlay";

interface EpisodeGridProps {
  episodes: EpisodeItem[];
  seriesTitle?: string;
  onPlayComplete?: () => void;
}

function episodeBadge(ep: EpisodeItem): { label: string; className: string } {
  if (ep.pipeline_status === "ready" && ep.manifest_url) {
    return {
      label: "Listo",
      className: "bg-emerald-500/20 text-emerald-300",
    };
  }
  if (ep.has_local_media) {
    return {
      label: "En biblioteca",
      className: "bg-sky-500/20 text-sky-300",
    };
  }
  if (ep.pipeline_status === "failed") {
    return {
      label: "No disponible",
      className: "bg-red-500/20 text-red-300",
    };
  }
  return {
    label: "Sin archivo",
    className: "bg-white/10 text-stream-muted",
  };
}

function playButtonLabel(ep: EpisodeItem, isLoading: boolean, pollStage: string | null): string {
  if (isLoading) {
    if (pollStage) return pollStage;
    return "Preparando…";
  }
  if (ep.pipeline_status === "ready" && ep.manifest_url) {
    return "Reproducir";
  }
  if (ep.pipeline_status === "failed") {
    return "Reintentar";
  }
  if (ep.has_local_media) {
    return "Transcodificar y ver";
  }
  return "Buscar y descargar";
}

function canPlay(ep: EpisodeItem): boolean {
  if (ep.pipeline_status === "ready" && ep.manifest_url) return true;
  if (ep.pipeline_status === "failed") return true;
  if (ep.has_local_media) return true;
  return true;
}

function needsAcquire(ep: EpisodeItem): boolean {
  if (ep.pipeline_status === "ready" && ep.manifest_url) return false;
  if (ep.has_local_media) return false;
  return true;
}

export function EpisodeGrid({ episodes, seriesTitle, onPlayComplete }: EpisodeGridProps) {
  const navigate = useNavigate();
  const {
    play,
    acquire,
    loadingId,
    pollStage,
    elapsedSeconds,
    error,
    errorEpisodeId,
    clearError,
  } = useEpisodePlay();

  async function handlePlay(ep: EpisodeItem) {
    clearError();
    if (ep.pipeline_status === "ready" && ep.manifest_url) {
      navigate(`/watch/${ep.id}`);
      return;
    }
    if (!canPlay(ep)) return;
    const run = needsAcquire(ep) ? acquire : play;
    const manifest = await run(ep.id, onPlayComplete);
    if (manifest) navigate(`/watch/${ep.id}`);
  }

  return (
    <div className="space-y-3">
      {episodes.map((ep) => {
        const title = ep.title || `Episodio ${ep.episode_number}`;
        const runtime = ep.runtime_minutes ? `${ep.runtime_minutes} min` : "";
        const isLoading = loadingId === ep.id;
        const badge = episodeBadge(ep);
        const rowError = errorEpisodeId === ep.id ? error : null;

        return (
          <article
            key={ep.id}
            className="group flex gap-4 rounded-xl border border-stream-border/60 bg-stream-surface/50 p-4 transition hover:border-white/20 hover:bg-stream-elevated/80"
          >
            <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-stream-elevated">
              {ep.still_url ? (
                <img
                  src={ep.still_url}
                  alt=""
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-lg font-bold text-stream-accent">
                  {ep.episode_number}
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-semibold">
                  {ep.season_number}x{String(ep.episode_number).padStart(2, "0")} · {title}
                </h3>
                <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${badge.className}`}>
                  {badge.label}
                </span>
                {runtime && (
                  <span className="text-xs text-stream-muted">{runtime}</span>
                )}
              </div>
              {ep.overview && (
                <p className="mt-1 line-clamp-2 text-sm text-stream-muted">
                  {ep.overview}
                </p>
              )}
              {(ep.error_message && ep.pipeline_status === "failed") || rowError ? (
                <p className="mt-1 text-xs text-red-300">
                  {rowError || ep.error_message}
                </p>
              ) : null}
            </div>
            <div className="flex shrink-0 flex-col items-end justify-center gap-2">
              {isLoading && elapsedSeconds > 0 && (
                <span className="text-xs text-stream-muted">
                  {Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, "0")}
                </span>
              )}
              <button
                type="button"
                disabled={isLoading || !canPlay(ep)}
                onClick={() => handlePlay(ep)}
                className="rounded bg-stream-accent px-4 py-2 text-sm font-semibold transition hover:bg-stream-accent-hover disabled:opacity-50"
              >
                {playButtonLabel(ep, isLoading, pollStage)}
              </button>
            </div>
          </article>
        );
      })}
      {!episodes.length && (
        <p className="py-8 text-center text-stream-muted">
          No hay episodios en esta temporada.
        </p>
      )}
    </div>
  );
}
