import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchActiveDownloads } from "../api/client";
import type { ActiveDownloadItem } from "../api/types";

const POLL_MS = 5000;

export function DownloadActivity() {
  const [items, setItems] = useState<ActiveDownloadItem[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetchActiveDownloads();
        if (!cancelled) setItems(res.items);
      } catch {
        if (!cancelled) setItems([]);
      }
    }

    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <div className="relative hidden md:block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-200 transition hover:bg-amber-500/20"
        aria-expanded={open}
      >
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-400" />
        {items.length} descarga{items.length === 1 ? "" : "s"}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-stream-border bg-stream-surface p-3 shadow-xl">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stream-muted">
            Actividad
          </p>
          <ul className="max-h-48 space-y-2 overflow-y-auto text-sm">
            {items.map((d) => (
              <li key={d.id} className="flex justify-between gap-2">
                <span className="truncate">
                  S{d.season_number}E{d.episode_number}
                  {d.title ? ` · ${d.title}` : ""}
                </span>
                <span className="shrink-0 text-xs text-stream-muted">
                  {d.pipeline_status}
                </span>
              </li>
            ))}
          </ul>
          <Link
            to="/settings"
            className="mt-3 block text-xs text-stream-accent hover:underline"
            onClick={() => setOpen(false)}
          >
            Ver en Ajustes →
          </Link>
        </div>
      )}
    </div>
  );
}
