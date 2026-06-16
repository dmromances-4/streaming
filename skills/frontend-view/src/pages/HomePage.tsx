import { useEffect, useState } from "react";
import {
  fetchCatalog,
  fetchLocalLibrary,
  fetchStats,
  fetchTopGenres,
  scanAllLibrary,
} from "../api/client";
import type { CatalogItem } from "../api/types";
import { ContinueWatchingRow } from "../components/ContinueWatchingRow";
import { LiveNowRow } from "../components/LiveNowRow";
import { ContentRow } from "../components/ContentRow";
import { HeroBanner } from "../components/HeroBanner";
import { HeroSkeleton, RowSkeleton } from "../components/LoadingSkeleton";
import { useCatalog } from "../hooks/useCatalog";

const ORIGINS = [
  { key: "american", label: "Series americanas", type: "series" },
  { key: "spanish", label: "Series españolas", type: "series" },
  { key: "european", label: "Películas europeas", type: "movie" },
  { key: "catalan", label: "Catalanas", type: undefined },
] as const;

const SCAN_SESSION_KEY = "library-scanned-session";

export function HomePage() {
  const featured = useCatalog({ limit: 1, cocteleria: true });
  const cocteleria = useCatalog({ cocteleria: true, limit: 20 });
  const [localLibrary, setLocalLibrary] = useState<CatalogItem[]>([]);
  const [localLoading, setLocalLoading] = useState(true);
  const [stats, setStats] = useState<{ ready: number; total: number } | null>(null);
  const [scanToast, setScanToast] = useState<string | null>(null);
  const [addToLibrary, setAddToLibrary] = useState<CatalogItem[]>([]);
  const [topGenres, setTopGenres] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchLocalLibrary(20)
      .then((res) => {
        if (!cancelled) setLocalLibrary(res.items);
      })
      .catch(() => {
        if (!cancelled) setLocalLibrary([]);
      })
      .finally(() => {
        if (!cancelled) setLocalLoading(false);
      });
    fetchStats()
      .then((s) => {
        if (!cancelled) setStats({ ready: s.ready, total: s.total });
      })
      .catch(() => {});
    fetchCatalog({ withoutLocal: true, type: "series", limit: 16 })
      .then((res) => {
        if (!cancelled) setAddToLibrary(res.items);
      })
      .catch(() => {});
    fetchTopGenres(4)
      .then((res) => {
        if (!cancelled) setTopGenres(res.genres);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (sessionStorage.getItem(SCAN_SESSION_KEY)) return;
    sessionStorage.setItem(SCAN_SESSION_KEY, "1");
    scanAllLibrary()
      .then((r) => {
        if (r.processed > 0) {
          setScanToast(`Biblioteca actualizada: ${r.processed} archivos enlazados`);
          fetchLocalLibrary(20).then((res) => setLocalLibrary(res.items));
        }
      })
      .catch(() => {});
  }, []);

  const heroItem = featured.items[0] ?? cocteleria.items[0];

  return (
    <div className="pb-16">
      {scanToast && (
        <div className="mx-4 mb-4 rounded-lg bg-emerald-500/20 px-4 py-2 text-sm text-emerald-200 md:mx-10">
          {scanToast}
        </div>
      )}

      {featured.loading && !heroItem ? (
        <HeroSkeleton />
      ) : heroItem ? (
        <HeroBanner item={heroItem} eagerImages />
      ) : null}

      {stats && (
        <p className="mb-4 px-4 text-sm text-stream-muted md:px-10">
          {stats.ready} títulos listos para reproducir · {stats.total} en catálogo
        </p>
      )}

      {localLoading ? (
        <RowSkeleton />
      ) : localLibrary.length > 0 ? (
        <ContentRow
          title="Disponible en tu biblioteca"
          items={localLibrary}
        />
      ) : null}

      <ContinueWatchingRow />

      <LiveNowRow />

      {addToLibrary.length > 0 && (
        <ContentRow
          title="Añade a tu biblioteca"
          items={addToLibrary}
          browseLink="/browse?type=series"
        />
      )}

      {topGenres.map((genre) => (
        <GenreRow key={genre} genre={genre} />
      ))}

      {cocteleria.loading ? (
        <RowSkeleton />
      ) : (
        <ContentRow
          title="Modo cóctel"
          items={cocteleria.items}
          browseLink="/browse?cocteleria=1"
        />
      )}

      {ORIGINS.map(({ key, label, type }) => (
        <OriginRow key={key} origin={key} label={label} type={type} />
      ))}
    </div>
  );
}

function GenreRow({ genre }: { genre: string }) {
  const { items, loading } = useCatalog({ genre, limit: 16 });
  if (loading) return <RowSkeleton />;
  if (items.length === 0) return null;
  return (
    <ContentRow
      title={genre}
      items={items}
      browseLink={`/browse?genre=${encodeURIComponent(genre)}`}
    />
  );
}

function OriginRow({
  origin,
  label,
  type,
}: {
  origin: string;
  label: string;
  type?: string;
}) {
  const { items, loading } = useCatalog({
    origin,
    type,
    limit: 20,
  });

  if (loading) return <RowSkeleton />;
  return (
    <ContentRow
      title={label}
      items={items}
      browseLink={`/browse?origin=${origin}${type ? `&type=${type}` : ""}`}
    />
  );
}
