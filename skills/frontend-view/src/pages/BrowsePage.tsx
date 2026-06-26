import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { fetchCatalog, requestTitle, searchTmdb } from "../api/client";
import type { CatalogItem, TmdbSearchResult } from "../api/types";
import { TitleCard } from "../components/TitleCard";
import { CardSkeleton } from "../components/LoadingSkeleton";

const PAGE_SIZE = 40;
const ORIGINS = [
  { key: "", label: "Todos los orígenes" },
  { key: "american", label: "Americano" },
  { key: "spanish", label: "Español" },
  { key: "european", label: "Europeo" },
  { key: "catalan", label: "Catalán" },
];

export function BrowsePage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [tmdbItems, setTmdbItems] = useState<TmdbSearchResult[]>([]);
  const [tmdbLoading, setTmdbLoading] = useState(false);
  const [requestingId, setRequestingId] = useState<number | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const q = params.get("q") || "";
  const type = params.get("type") || "";
  const origin = params.get("origin") || "";
  const status = params.get("status") || "";
  const cocteleria = params.get("cocteleria") === "1";
  const genre = params.get("genre") || "";

  const [searchInput, setSearchInput] = useState(q);

  useEffect(() => {
    setSearchInput(q);
    setOffset(0);
  }, [q, type, origin, status, cocteleria, genre]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const trimmed = searchInput.trim();
      const next = new URLSearchParams(params);
      if (trimmed) next.set("q", trimmed);
      else next.delete("q");
      if (next.get("q") !== (params.get("q") || "")) setParams(next, { replace: true });
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput, params, setParams]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCatalog({
      q: q || undefined,
      type: type || undefined,
      origin: origin || undefined,
      status: status || undefined,
      cocteleria: cocteleria || undefined,
      genre: genre || undefined,
      limit: PAGE_SIZE,
      offset,
    })
      .then((res) => {
        if (cancelled) return;
        setItems((prev) => (offset === 0 ? res.items : [...prev, ...res.items]));
        setTotal(res.total);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error al cargar");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [q, type, origin, status, cocteleria, genre, offset]);

  useEffect(() => {
    if (!q || loading || items.length > 0 || offset > 0) {
      setTmdbItems([]);
      return;
    }
    let cancelled = false;
    setTmdbLoading(true);
    searchTmdb(
      q,
      type === "movie" || type === "series" ? type : undefined
    )
      .then((res) => {
        if (!cancelled) setTmdbItems(res.items);
      })
      .catch(() => {
        if (!cancelled) setTmdbItems([]);
      })
      .finally(() => {
        if (!cancelled) setTmdbLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q, type, loading, items.length, offset]);

  async function handleRequestTmdb(item: TmdbSearchResult) {
    setRequestingId(item.tmdb_id);
    try {
      const created = await requestTitle(
        item.tmdb_id,
        item.content_type as "movie" | "series"
      );
      navigate(`/title/${created.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo solicitar el título");
    } finally {
      setRequestingId(null);
    }
  }

  function setFilter(key: string, value: string) {
    const n = new URLSearchParams(params);
    if (value) n.set(key, value);
    else n.delete(key);
    setParams(n);
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-16 md:px-10">
      <h1 className="mb-6 text-2xl font-bold md:text-3xl">Explorar</h1>

      <input
        type="search"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder="Buscar títulos, reparto, géneros…"
        className="mb-6 w-full rounded-lg border border-stream-border bg-stream-surface px-4 py-2.5 text-sm outline-none focus:border-stream-accent"
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <FilterChip label="Todo" active={!type && !cocteleria} onClick={() => {
          const n = new URLSearchParams(params);
          n.delete("type");
          n.delete("cocteleria");
          setParams(n);
        }} />
        <FilterChip label="Series" active={type === "series"} onClick={() => setFilter("type", type === "series" ? "" : "series")} />
        <FilterChip label="Películas" active={type === "movie"} onClick={() => setFilter("type", type === "movie" ? "" : "movie")} />
        <FilterChip label="Coctelería" active={cocteleria} onClick={() => setFilter("cocteleria", cocteleria ? "" : "1")} />
        <FilterChip label="Listos" active={status === "ready"} onClick={() => setFilter("status", status === "ready" ? "" : "ready")} />
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {ORIGINS.map((o) => (
          <FilterChip
            key={o.key || "all"}
            label={o.label}
            active={origin === o.key}
            onClick={() => setFilter("origin", origin === o.key ? "" : o.key)}
          />
        ))}
      </div>

      <p className="mb-4 text-sm text-stream-muted">
        {total} título{total !== 1 ? "s" : ""}
        {q ? ` para "${q}"` : ""}
      </p>

      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

      {!loading && items.length === 0 && !tmdbLoading && tmdbItems.length === 0 && (
        <p className="rounded-lg bg-stream-surface p-8 text-center text-stream-muted">
          Sin resultados{q ? ` para "${q}"` : ""}. Prueba otro término o quita filtros.
        </p>
      )}

      {!loading && items.length === 0 && (tmdbLoading || tmdbItems.length > 0) && (
        <section className="mb-8">
          <h2 className="mb-2 text-lg font-semibold">Buscar en TMDB</h2>
          <p className="mb-4 text-sm text-stream-muted">
            No está en tu catálogo local. Solicítalo para buscar torrent y descargar automáticamente.
          </p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {tmdbLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <CardSkeleton key={`tmdb-sk-${i}`} />
              ))}
            {!tmdbLoading &&
              tmdbItems.map((item) => (
                <div
                  key={`${item.content_type}-${item.tmdb_id}`}
                  className="flex flex-col overflow-hidden rounded-lg border border-stream-border bg-stream-surface"
                >
                  {item.poster_url ? (
                    <img
                      src={item.poster_url}
                      alt={item.title}
                      className="aspect-[2/3] w-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="flex aspect-[2/3] items-center justify-center bg-stream-elevated text-xs text-stream-muted">
                      Sin póster
                    </div>
                  )}
                  <div className="flex flex-1 flex-col p-3">
                    <p className="line-clamp-2 text-sm font-semibold">{item.title}</p>
                    <p className="mt-1 text-xs text-stream-muted">
                      {item.year ?? "—"} · {item.content_type === "series" ? "Serie" : "Película"}
                    </p>
                    <button
                      type="button"
                      disabled={requestingId === item.tmdb_id}
                      onClick={() => handleRequestTmdb(item)}
                      className="mt-3 rounded bg-stream-accent px-3 py-2 text-xs font-semibold text-white hover:bg-stream-accent-hover disabled:opacity-50"
                    >
                      {requestingId === item.tmdb_id ? "Solicitando…" : "Solicitar descarga"}
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {items.map((item) => (
          <TitleCard key={item.id} item={item} className="w-full" />
        ))}
        {loading &&
          Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={`sk-${i}`} />
          ))}
      </div>

      {!loading && items.length < total && (
        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={() => setOffset((o) => o + PAGE_SIZE)}
            className="rounded-lg border border-stream-border px-6 py-2.5 text-sm font-medium hover:bg-stream-surface"
          >
            Cargar más
          </button>
        </div>
      )}
    </div>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
        active
          ? "bg-white text-black"
          : "bg-stream-surface text-stream-muted hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}
