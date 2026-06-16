import { useCallback, useEffect, useState } from "react";

const FAVORITES_KEY = "live:favorites";
const RECENT_KEY = "live:recent";
const MAX_RECENT = 12;

export function useLiveFavorites() {
  const [favorites, setFavorites] = useState<string[]>([]);
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    try {
      const fav = localStorage.getItem(FAVORITES_KEY);
      const rec = localStorage.getItem(RECENT_KEY);
      if (fav) setFavorites(JSON.parse(fav) as string[]);
      if (rec) setRecent(JSON.parse(rec) as string[]);
    } catch {
      setFavorites([]);
      setRecent([]);
    }
  }, []);

  const toggleFavorite = useCallback((channelId: string) => {
    setFavorites((prev) => {
      const next = prev.includes(channelId)
        ? prev.filter((id) => id !== channelId)
        : [...prev, channelId];
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isFavorite = useCallback(
    (channelId: string) => favorites.includes(channelId),
    [favorites]
  );

  const pushRecent = useCallback((channelId: string) => {
    setRecent((prev) => {
      const next = [channelId, ...prev.filter((id) => id !== channelId)].slice(
        0,
        MAX_RECENT
      );
      localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { favorites, recent, toggleFavorite, isFavorite, pushRecent };
}
