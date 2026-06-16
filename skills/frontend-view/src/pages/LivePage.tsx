import { useEffect, useMemo, useState } from "react";
import { fetchLiveChannels } from "../api/client";
import type { LiveChannel, LiveCountry } from "../api/types";
import { LiveChannelCard } from "../components/LiveChannelCard";
import { LiveChannelSearch } from "../components/LiveChannelSearch";
import { LiveCountryFilter } from "../components/LiveCountryFilter";
import { LiveFavoritesRow } from "../components/LiveFavoritesRow";
import { LiveGridSkeleton } from "../components/LoadingSkeleton";
import { LiveRegionFilter } from "../components/LiveRegionFilter";
import { useLiveFavorites } from "../hooks/useLiveFavorites";

function isAutonomic(ch: LiveChannel): boolean {
  return (ch.tags || []).some((t) => t.toLowerCase() === "autonomic");
}

function groupChannels(channels: LiveChannel[]): Record<string, LiveChannel[]> {
  const grouped: Record<string, LiveChannel[]> = {};
  for (const ch of channels) {
    const countryName = ch.country_name || "Internacional";
    const label = `${countryName} · ${ch.group || "General"}`;
    if (!grouped[label]) grouped[label] = [];
    grouped[label].push(ch);
  }
  return grouped;
}

function matchesSearch(ch: LiveChannel, q: string): boolean {
  const needle = q.toLowerCase();
  return (
    ch.name.toLowerCase().includes(needle) ||
    (ch.country_name || "").toLowerCase().includes(needle) ||
    (ch.group || "").toLowerCase().includes(needle) ||
    (ch.region || "").toLowerCase().includes(needle) ||
    ch.id.toLowerCase().includes(needle)
  );
}

export function LivePage() {
  const [allChannels, setAllChannels] = useState<LiveChannel[]>([]);
  const [countryChannels, setCountryChannels] = useState<LiveChannel[]>([]);
  const [countries, setCountries] = useState<LiveCountry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [country, setCountry] = useState("");
  const [region, setRegion] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const { favorites, recent, toggleFavorite, isFavorite } = useLiveFavorites();

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    if (country !== "ES") setRegion("");
  }, [country]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchLiveChannels({
      country: country || undefined,
      q: !country && debouncedSearch ? debouncedSearch : undefined,
    })
      .then((res) => {
        if (cancelled) return;
        setCountries(res.countries);
        setCountryChannels(res.channels);
        if (!country && !debouncedSearch) {
          setAllChannels(res.channels);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "No se pudieron cargar los canales");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [country, debouncedSearch]);

  useEffect(() => {
    if (allChannels.length === 0 && !loading && !error) {
      fetchLiveChannels()
        .then((res) => setAllChannels(res.channels))
        .catch(() => {});
    }
  }, [allChannels.length, loading, error]);

  const esRegions = useMemo(() => {
    const source = country === "ES" ? countryChannels : allChannels.filter((c) => c.country === "ES");
    const regions = new Set<string>();
    for (const ch of source) {
      if (ch.region) regions.add(ch.region);
    }
    return Array.from(regions).sort((a, b) => a.localeCompare(b, "es"));
  }, [allChannels, country, countryChannels]);

  const filteredChannels = useMemo(() => {
    let items = country ? countryChannels : allChannels;

    if (country === "ES" && region === "__nacional__") {
      items = items.filter((ch) => !isAutonomic(ch));
    } else if (country === "ES" && region === "__autonomic__") {
      items = items.filter(isAutonomic);
    } else if (country === "ES" && region) {
      items = items.filter((ch) => ch.region === region);
    }

    if (debouncedSearch) {
      items = items.filter((ch) => matchesSearch(ch, debouncedSearch));
    }

    return items;
  }, [allChannels, country, countryChannels, region, debouncedSearch]);

  const groups = useMemo(() => groupChannels(filteredChannels), [filteredChannels]);
  const totalVisible = filteredChannels.length;

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-16 md:px-10">
      <h1 className="mb-2 text-2xl font-bold md:text-3xl">TV pública europea</h1>
      <p className="mb-6 text-sm text-stream-muted">
        Emisoras públicas de la UE y EEA en directo — {allChannels.length || "…"} canales
      </p>

      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <LiveChannelSearch value={search} onChange={setSearch} />
      </div>

      <div className="mb-8">
        <LiveCountryFilter
          countries={countries}
          selected={country}
          onSelect={setCountry}
        />
      </div>

      {country === "ES" && (
        <LiveRegionFilter regions={esRegions} selected={region} onSelect={setRegion} />
      )}

      {loading && allChannels.length === 0 ? (
        <LiveGridSkeleton />
      ) : error ? (
        <p className="text-red-300">{error}</p>
      ) : (
        <>
          <LiveFavoritesRow
            title="Favoritos"
            channelIds={favorites}
            allChannels={allChannels}
            favorites={favorites}
            onToggleFavorite={toggleFavorite}
          />
          <LiveFavoritesRow
            title="Vistos recientemente"
            channelIds={recent}
            allChannels={allChannels}
            favorites={favorites}
            onToggleFavorite={toggleFavorite}
          />

          {totalVisible === 0 ? (
            <p className="py-12 text-center text-stream-muted">
              No hay canales que coincidan con tu búsqueda.
            </p>
          ) : (
            Object.entries(groups).map(([group, channels]) => (
              <section key={group} className="mb-10">
                <h2 className="mb-4 text-lg font-semibold">{group}</h2>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                  {channels.map((ch) => (
                    <LiveChannelCard
                      key={ch.id}
                      channel={ch}
                      isFavorite={isFavorite(ch.id)}
                      onToggleFavorite={toggleFavorite}
                    />
                  ))}
                </div>
              </section>
            ))
          )}
        </>
      )}
    </div>
  );
}
