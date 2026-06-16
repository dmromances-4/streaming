import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { fetchSystemStatus } from "../api/client";
import { DownloadActivity } from "./DownloadActivity";

function liveFavoritesCount(): number {
  try {
    const raw = localStorage.getItem("live:favorites");
    if (!raw) return 0;
    const list = JSON.parse(raw) as unknown;
    return Array.isArray(list) ? list.length : 0;
  } catch {
    return 0;
  }
}

export function Layout() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [acquireReady, setAcquireReady] = useState<boolean | null>(null);
  const [liveFavCount, setLiveFavCount] = useState(0);

  useEffect(() => {
    fetchSystemStatus()
      .then((s) => setAcquireReady(s.acquire_ready))
      .catch(() => setAcquireReady(null));
    setLiveFavCount(liveFavoritesCount());
    const onStorage = () => setLiveFavCount(liveFavoritesCount());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = search.trim();
    if (q) navigate(`/browse?q=${encodeURIComponent(q)}`);
    else navigate("/browse");
  }

  return (
    <div className="min-h-screen">
      {acquireReady === false && (
        <div className="fixed top-0 z-[60] w-full bg-amber-500/95 px-4 py-2 text-center text-sm font-medium text-black">
          Las descargas torrent no están configuradas.{" "}
          <Link to="/settings" className="underline hover:no-underline">
            Configurar Prowlarr
          </Link>
        </div>
      )}
      <header
        className={`fixed z-50 w-full bg-gradient-to-b from-black/80 to-transparent px-4 py-4 md:px-10 ${
          acquireReady === false ? "top-9" : "top-0"
        }`}
      >
        <div className="mx-auto flex max-w-[1400px] items-center gap-4">
          <Link
            to="/"
            className="shrink-0 text-2xl font-extrabold tracking-tight text-stream-accent"
          >
            STREAM
          </Link>
          <form onSubmit={handleSearch} className="hidden flex-1 md:block md:max-w-md">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar títulos…"
              className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-2 text-sm outline-none focus:border-stream-accent"
            />
          </form>
          <DownloadActivity />
          <nav className="ml-auto flex items-center gap-4 text-sm font-medium text-white/90 sm:gap-6">
            <Link to="/" className="transition hover:text-white">
              Inicio
            </Link>
            <Link to="/live" className="relative transition hover:text-white">
              En directo
              {liveFavCount > 0 && (
                <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-stream-accent px-1 text-[10px] font-bold text-white">
                  {liveFavCount}
                </span>
              )}
            </Link>
            <Link to="/browse" className="transition hover:text-white">
              Explorar
            </Link>
            <Link to="/settings" className="hidden transition hover:text-white sm:inline">
              Ajustes
            </Link>
          </nav>
        </div>
      </header>
      <main className={acquireReady === false ? "pt-28" : "pt-16"}>
        <Outlet />
      </main>
    </div>
  );
}
