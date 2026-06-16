import { Link } from "react-router-dom";
import type { CatalogItem } from "../api/types";

interface HeroBannerProps {
  item: CatalogItem;
  eagerImages?: boolean;
}

export function HeroBanner({ item, eagerImages = false }: HeroBannerProps) {
  const bg = item.backdrop_url || item.poster_url;
  const isSeries = item.content_type === "series";
  const watchLink = isSeries
    ? `/title/${item.id}`
    : item.manifest_url
      ? `/watch/movie/${item.id}`
      : `/title/${item.id}`;

  return (
    <section className="relative mb-10 h-[55vh] min-h-[360px] w-full overflow-hidden md:h-[70vh]">
      {bg && (
        <img
          src={bg}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
          loading={eagerImages ? "eager" : "lazy"}
          fetchPriority={eagerImages ? "high" : "auto"}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-r from-black via-black/70 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-stream-bg via-transparent to-black/30" />
      <div className="relative flex h-full max-w-[1400px] flex-col justify-end px-4 pb-12 md:px-10 md:pb-16">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-stream-accent">
          Destacado
        </p>
        <h1 className="max-w-2xl text-3xl font-extrabold leading-tight md:text-5xl">
          {item.title}
        </h1>
        {item.year && (
          <p className="mt-2 text-sm text-white/70">{item.year}</p>
        )}
        {item.overview && (
          <p className="mt-4 line-clamp-3 max-w-xl text-sm text-white/80 md:text-base">
            {item.overview}
          </p>
        )}
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to={watchLink}
            className="inline-flex items-center gap-2 rounded bg-white px-6 py-2.5 text-sm font-bold text-black transition hover:bg-white/90"
          >
            ▶ {isSeries ? "Ver episodios" : "Reproducir"}
          </Link>
          <Link
            to={`/title/${item.id}`}
            className="inline-flex items-center gap-2 rounded bg-white/20 px-6 py-2.5 text-sm font-semibold backdrop-blur transition hover:bg-white/30"
          >
            Más información
          </Link>
        </div>
      </div>
    </section>
  );
}
