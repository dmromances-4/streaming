import { useNavigate } from "react-router-dom";
import type { LiveChannel } from "../api/types";
import { countryFlag } from "../lib/countryFlags";

interface LiveChannelSidebarProps {
  channels: LiveChannel[];
  currentId: string;
  favorites: string[];
  onToggleFavorite: (id: string) => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function LiveChannelSidebar({
  channels,
  currentId,
  favorites,
  onToggleFavorite,
  mobileOpen = false,
  onCloseMobile,
}: LiveChannelSidebarProps) {
  const navigate = useNavigate();

  function selectChannel(id: string) {
    navigate(`/live/${id}`);
    onCloseMobile?.();
  }

  const content = (
    <div className="flex h-full flex-col">
      <div className="border-b border-stream-border px-4 py-3">
        <h2 className="text-sm font-semibold">Cambiar canal</h2>
        <p className="text-xs text-stream-muted">{channels.length} canales</p>
      </div>
      <ul className="flex-1 overflow-y-auto py-2">
        {channels.map((ch) => {
          const active = ch.id === currentId;
          const fav = favorites.includes(ch.id);
          return (
            <li key={ch.id}>
              <button
                type="button"
                onClick={() => selectChannel(ch.id)}
                className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition ${
                  active
                    ? "bg-stream-accent/20 text-white"
                    : "text-white/85 hover:bg-stream-elevated"
                }`}
              >
                <span className="text-base">{countryFlag(ch.country)}</span>
                <span className="min-w-0 flex-1 truncate">{ch.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleFavorite(ch.id);
                  }}
                  className={`shrink-0 text-xs ${fav ? "text-amber-400" : "text-white/30"}`}
                  aria-label="Favorito"
                >
                  {fav ? "★" : "☆"}
                </button>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );

  return (
    <>
      <aside className="hidden w-[280px] shrink-0 border-r border-stream-border bg-stream-surface/95 lg:block">
        {content}
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            onClick={onCloseMobile}
            aria-label="Cerrar"
          />
          <div className="absolute bottom-0 left-0 right-0 max-h-[70vh] rounded-t-2xl bg-stream-surface">
            {content}
          </div>
        </div>
      )}
    </>
  );
}
