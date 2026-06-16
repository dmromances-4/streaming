import { Link } from "react-router-dom";
import type { LiveChannel } from "../api/types";
import { countryFlag } from "../lib/countryFlags";

interface LiveChannelCardProps {
  channel: LiveChannel;
  isFavorite?: boolean;
  onToggleFavorite?: (id: string) => void;
  compact?: boolean;
}

export function LiveChannelCard({
  channel,
  isFavorite = false,
  onToggleFavorite,
  compact = false,
}: LiveChannelCardProps) {
  return (
    <Link
      to={`/live/${channel.id}`}
      className={`group relative flex flex-col items-center gap-2 rounded-xl border border-stream-border bg-stream-surface transition hover:border-stream-accent hover:bg-stream-elevated ${
        compact ? "min-w-[120px] shrink-0 p-3" : "gap-3 p-4"
      }`}
    >
      {onToggleFavorite && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggleFavorite(channel.id);
          }}
          className={`absolute right-2 top-2 rounded-full p-1 text-sm transition ${
            isFavorite ? "text-amber-400" : "text-white/30 hover:text-amber-300"
          }`}
          aria-label={isFavorite ? "Quitar de favoritos" : "Añadir a favoritos"}
        >
          {isFavorite ? "★" : "☆"}
        </button>
      )}
      <div className="relative">
        {channel.logo ? (
          <img
            src={channel.logo}
            alt=""
            className={`rounded-lg object-contain ${compact ? "h-10 w-10" : "h-12 w-12"}`}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div
            className={`flex items-center justify-center rounded-lg bg-stream-elevated font-bold ${
              compact ? "h-10 w-10 text-base" : "h-12 w-12 text-lg"
            }`}
          >
            {channel.name.charAt(0)}
          </div>
        )}
        <span className="absolute -bottom-1 -right-1 text-xs" title={channel.country_name || ""}>
          {countryFlag(channel.country)}
        </span>
      </div>
      <span className={`text-center font-medium ${compact ? "text-xs" : "text-sm"}`}>
        {channel.name}
      </span>
      {!compact && (
        <div className="flex flex-wrap justify-center gap-1">
          <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-red-300">
            En directo
          </span>
          {channel.drm && (
            <span className="rounded bg-purple-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-purple-300">
              DRM
            </span>
          )}
          {channel.requires_vpn && (
            <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300">
              VPN
            </span>
          )}
          {channel.auth_provider && (
            <span className="rounded bg-blue-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-blue-300">
              Login
            </span>
          )}
          {channel.tags?.some((t) => t.toLowerCase() === "autonomic") && (
            <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
              Autonómica
            </span>
          )}
          {channel.geo_country && (
            <span className="rounded bg-orange-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-orange-300">
              {channel.geo_country}
            </span>
          )}
        </div>
      )}
    </Link>
  );
}
