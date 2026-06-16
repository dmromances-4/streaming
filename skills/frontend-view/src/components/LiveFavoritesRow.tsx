import type { LiveChannel } from "../api/types";
import { LiveChannelCard } from "./LiveChannelCard";

interface LiveFavoritesRowProps {
  title: string;
  channelIds: string[];
  allChannels: LiveChannel[];
  favorites: string[];
  onToggleFavorite: (id: string) => void;
}

export function LiveFavoritesRow({
  title,
  channelIds,
  allChannels,
  favorites,
  onToggleFavorite,
}: LiveFavoritesRowProps) {
  const byId = new Map(allChannels.map((c) => [c.id, c]));
  const items = channelIds.map((id) => byId.get(id)).filter(Boolean) as LiveChannel[];

  if (items.length === 0) return null;

  return (
    <section className="mb-8">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {items.map((ch) => (
          <LiveChannelCard
            key={ch.id}
            channel={ch}
            compact
            isFavorite={favorites.includes(ch.id)}
            onToggleFavorite={onToggleFavorite}
          />
        ))}
      </div>
    </section>
  );
}
