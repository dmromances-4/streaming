import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchSimilarTitles } from "../api/client";
import type { CatalogItem } from "../api/types";
import { ContentRow } from "../components/ContentRow";
import { EpisodeGrid } from "../components/EpisodeGrid";
import { EpisodeSkeleton } from "../components/LoadingSkeleton";
import { SeasonTabs } from "../components/SeasonTabs";
import { useMoviePlay } from "../hooks/useMoviePlay";
import { useSeries } from "../hooks/useSeries";

export function TitlePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    play: playMovieFlow,
    loading: movieLoading,
    pollStage: moviePollStage,
    elapsedSeconds: movieElapsed,
    error: movieError,
    clearError: clearMovieError,
  } = useMoviePlay();
  const [similar, setSimilar] = useState<CatalogItem[]>([]);

  const {
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
  } = useSeries(id);

  useEffect(() => {
    if (!id) return;
    fetchSimilarTitles(id)
      .then((res) => setSimilar(res.items))
      .catch(() => setSimilar([]));
  }, [id]);

  useEffect(() => {
    if (!title) return;
    const urls = [title.poster_url, title.backdrop_url].filter(Boolean) as string[];
    const links: HTMLLinkElement[] = [];
    for (const url of urls) {
      const link = document.createElement("link");
      link.rel = "preload";
      link.as = "image";
      link.href = url;
      document.head.appendChild(link);
      links.push(link);
    }
    return () => {
      for (const link of links) {
        link.remove();
      }
    };
  }, [title?.poster_url, title?.backdrop_url]);

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-[40vh] bg-stream-elevated" />
        <div className="mx-auto max-w-[1400px] space-y-4 px-4 py-8 md:px-10">
          <div className="h-8 w-64 rounded bg-stream-elevated" />
          <div className="h-20 rounded bg-stream-elevated" />
        </div>
      </div>
    );
  }

  if (error || !title) {
    return (
      <div className="px-4 py-20 text-center md:px-10">
        <p className="text-red-300">{error || "Título no encontrado"}</p>
        <Link to="/" className="mt-4 inline-block text-stream-accent">
          Volver al inicio
        </Link>
      </div>
    );
  }

  const bg = title.backdrop_url || title.poster_url;
  const isSeries = title.content_type === "series";

  async function handlePlayMovie() {
    if (!id) return;
    clearMovieError();
    if (title.pipeline_status === "ready" && title.manifest_url) {
      navigate(`/watch/movie/${id}`);
      return;
    }
    const manifest = await playMovieFlow(id);
    if (manifest) navigate(`/watch/movie/${id}`);
  }

  const movieButtonLabel = movieLoading
    ? moviePollStage
      ? movieElapsed > 0
        ? `${moviePollStage} (${Math.floor(movieElapsed / 60)}:${String(movieElapsed % 60).padStart(2, "0")})`
        : moviePollStage
      : "Preparando…"
    : "▶ Reproducir";

  return (
    <div className="pb-16">
      <section className="relative min-h-[45vh] overflow-hidden">
        {bg && (
          <img
            src={bg}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            loading="eager"
            fetchPriority="high"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-stream-bg via-stream-bg/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-stream-bg/90 to-transparent" />

        <div className="relative mx-auto flex max-w-[1400px] gap-6 px-4 py-12 md:px-10 md:py-16">
          {title.poster_url && (
            <img
              src={title.poster_url}
              alt={title.title}
              className="hidden h-56 w-40 shrink-0 rounded-lg object-cover shadow-2xl md:block lg:h-72 lg:w-48"
              loading="eager"
              fetchPriority="high"
            />
          )}
          <div className="flex-1">
            <h1 className="text-3xl font-extrabold md:text-5xl">{title.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-stream-muted">
              {title.year && <span>{title.year}</span>}
              {title.runtime_minutes && (
                <span>{title.runtime_minutes} min</span>
              )}
              <span className="capitalize">{title.origin}</span>
            </div>
            {title.genres.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {title.genres.map((g) => (
                  <span
                    key={g}
                    className="rounded-full border border-white/20 px-3 py-1 text-xs"
                  >
                    {g}
                  </span>
                ))}
              </div>
            )}
            {title.overview && (
              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-white/85 md:text-base">
                {title.overview}
              </p>
            )}
            {title.cast.length > 0 && (
              <p className="mt-3 text-sm text-stream-muted">
                <span className="font-medium text-white/70">Reparto: </span>
                {title.cast.slice(0, 6).join(" · ")}
              </p>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              {!isSeries && (
                <button
                  type="button"
                  onClick={handlePlayMovie}
                  disabled={movieLoading}
                  className="rounded bg-white px-6 py-2.5 text-sm font-bold text-black hover:bg-white/90 disabled:opacity-60"
                >
                  {movieButtonLabel}
                </button>
              )}
              {movieError && (
                <p className="w-full text-sm text-red-300">{movieError}</p>
              )}
              {isSeries && seasons.length > 0 && (
                <span className="rounded bg-white/15 px-4 py-2.5 text-sm">
                  {seasons.reduce((n, s) => n + s.ready_count, 0)}/
                  {seasons.reduce((n, s) => n + s.episode_count, 0)} listos
                  {scanning ? " · escaneando biblioteca…" : ""}
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {similar.length > 0 && (
        <section className="mx-auto max-w-[1400px] px-4 md:px-10">
          <ContentRow title="Títulos similares" items={similar} />
        </section>
      )}

      {isSeries && (
        <section className="mx-auto max-w-[1400px] px-4 md:px-10">
          <h2 className="mb-4 text-xl font-bold">Episodios</h2>
          {seasons.length > 0 ? (
            <>
              <SeasonTabs
                seasons={seasons}
                active={activeSeason}
                onChange={setActiveSeason}
              />
              <div className="mt-6">
                {episodesLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <EpisodeSkeleton key={i} />
                    ))}
                  </div>
                ) : (
                  <EpisodeGrid
                    episodes={episodes}
                    seriesTitle={title.title}
                    onPlayComplete={reloadEpisodes}
                  />
                )}
              </div>
            </>
          ) : (
            <p className="rounded-lg bg-stream-surface p-6 text-center text-stream-muted">
              Episodios no disponibles todavía. Vuelve a intentarlo en unos
              momentos.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
