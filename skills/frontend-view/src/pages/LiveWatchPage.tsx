import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchLiveChannelStream, fetchLiveChannels, resolveManifestUrl } from "../api/client";
import type { LiveChannel, LiveDrmConfig, LiveStreamRequirements } from "../api/types";
import { LiveChannelSidebar } from "../components/LiveChannelSidebar";
import { VideoPlayer } from "../components/VideoPlayer";
import { useLiveFavorites } from "../hooks/useLiveFavorites";

export function LiveWatchPage() {
  const { channelId } = useParams<{ channelId: string }>();
  const navigate = useNavigate();
  const [src, setSrc] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [countryCode, setCountryCode] = useState<string | null>(null);
  const [drm, setDrm] = useState<LiveDrmConfig | null>(null);
  const [requirements, setRequirements] = useState<LiveStreamRequirements | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [allChannels, setAllChannels] = useState<LiveChannel[]>([]);
  const [mobileGuideOpen, setMobileGuideOpen] = useState(false);
  const { favorites, toggleFavorite, pushRecent } = useLiveFavorites();

  const sidebarChannels = useMemo(() => {
    if (!channelId || allChannels.length === 0) return allChannels;
    const current = allChannels.find((c) => c.id === channelId);
    const code = current?.country;
    const sameCountry = code
      ? allChannels.filter((c) => c.country === code)
      : allChannels;
    const favSet = new Set(favorites);
    const favChannels = allChannels.filter((c) => favSet.has(c.id));
    const merged = new Map<string, LiveChannel>();
    for (const ch of [...favChannels, ...sameCountry, ...allChannels]) {
      merged.set(ch.id, ch);
    }
    return Array.from(merged.values());
  }, [allChannels, channelId, favorites]);

  useEffect(() => {
    if (!channelId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [stream, channelList] = await Promise.all([
          fetchLiveChannelStream(channelId!),
          fetchLiveChannels(),
        ]);
        if (!cancelled) {
          setAllChannels(channelList.channels);
          setSrc(resolveManifestUrl(stream.proxied_url));
          setName(stream.name || channelId!);
          setCountryCode(stream.country || null);
          setDrm(stream.drm ?? null);
          setRequirements(stream.requirements ?? null);
          pushRecent(channelId!);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "No se pudo cargar el canal (geo-block o mantenimiento)"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    const retry = setInterval(load, 5 * 60 * 1000);
    return () => {
      cancelled = true;
      clearInterval(retry);
    };
  }, [channelId, pushRecent]);

  if (loading && !src) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-stream-muted">
        Conectando con {channelId}…
      </div>
    );
  }

  if (error || !src) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="text-red-300">{error || "Canal no disponible"}</p>
        {requirements?.vpn && (
          <p className="mt-2 text-sm text-amber-200">
            Este canal requiere VPN UK. Usa{" "}
            <code className="text-white/80">docker-compose.vpn.yml</code>.
          </p>
        )}
        {requirements?.auth === "bbc" && (
          <p className="mt-2 text-sm text-amber-200">
            Configura <code className="text-white/80">BBC_IPLAYER_COOKIES</code> en Ajustes.
          </p>
        )}
        {requirements?.geo_country === "ES" && (
          <p className="mt-2 text-sm text-amber-200">
            Algunas TVs autonómicas solo están disponibles desde España o con acceso geo
            compatible.
          </p>
        )}
        <div className="mt-4 flex flex-col items-center gap-2">
          <Link to="/live" className="text-stream-accent">
            Volver a TV en directo
          </Link>
          {sidebarChannels.length > 1 && (
            <button
              type="button"
              onClick={() => {
                const other = sidebarChannels.find((c) => c.id !== channelId);
                if (other) navigate(`/live/${other.id}`);
              }}
              className="text-sm text-white/70 underline"
            >
              Probar otro canal
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <LiveChannelSidebar
        channels={sidebarChannels}
        currentId={channelId!}
        favorites={favorites}
        onToggleFavorite={toggleFavorite}
        mobileOpen={mobileGuideOpen}
        onCloseMobile={() => setMobileGuideOpen(false)}
      />
      <div className="relative min-w-0 flex-1">
        <div className="absolute left-4 top-4 z-10 flex flex-wrap items-center gap-2">
          <span className="rounded bg-red-600 px-2 py-1 text-xs font-bold uppercase">
            En directo
          </span>
          <span className="text-sm font-medium text-white/90">{name}</span>
          {countryCode && (
            <span className="rounded bg-black/50 px-2 py-0.5 text-xs text-white/80">
              {countryCode}
            </span>
          )}
          {drm && (
            <span className="rounded bg-purple-600/80 px-2 py-0.5 text-xs uppercase">
              DRM
            </span>
          )}
          {requirements?.geo_country === "ES" && (
            <span className="rounded bg-amber-600/70 px-2 py-0.5 text-xs text-white/90">
              Geo ES
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setMobileGuideOpen(true)}
          className="absolute right-4 top-4 z-10 rounded bg-black/60 px-3 py-2 text-sm lg:hidden"
        >
          Canales
        </button>
        <VideoPlayer
          src={src}
          title={name}
          live
          drm={drm}
          onBack={() => navigate("/live")}
        />
      </div>
    </div>
  );
}
