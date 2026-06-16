import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchLiveChannels } from "../api/client";
import type { LiveChannel } from "../api/types";
import { LiveChannelCard } from "./LiveChannelCard";
import { useLiveFavorites } from "../hooks/useLiveFavorites";

const DEFAULT_IDS = ["rtve-la1", "rtve-la2", "de-daserste", "fr-arte-fr", "pt-rtp1", "it-rai1"];

export function LiveNowRow() {
  const [channels, setChannels] = useState<LiveChannel[]>([]);
  const { favorites, toggleFavorite, isFavorite } = useLiveFavorites();

  useEffect(() => {
    fetchLiveChannels()
      .then((res) => setChannels(res.channels))
      .catch(() => {});
  }, []);

  const displayed = useMemo(() => {
    const byId = new Map(channels.map((c) => [c.id, c]));
    const picked: LiveChannel[] = [];
    for (const id of favorites) {
      const ch = byId.get(id);
      if (ch) picked.push(ch);
    }
    for (const id of DEFAULT_IDS) {
      if (picked.length >= 12) break;
      const ch = byId.get(id);
      if (ch && !picked.some((p) => p.id === ch.id)) picked.push(ch);
    }
    for (const ch of channels) {
      if (picked.length >= 12) break;
      if (!picked.some((p) => p.id === ch.id)) picked.push(ch);
    }
    return picked.slice(0, 12);
  }, [channels, favorites]);

  if (displayed.length === 0) return null;

  return (
    <section className="mb-10 px-4 md:px-10">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">En directo ahora</h2>
        <Link to="/live" className="text-sm text-stream-accent hover:underline">
          Ver toda la TV
        </Link>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {displayed.map((ch) => (
          <LiveChannelCard
            key={ch.id}
            channel={ch}
            compact
            isFavorite={isFavorite(ch.id)}
            onToggleFavorite={toggleFavorite}
          />
        ))}
      </div>
    </section>
  );
}
