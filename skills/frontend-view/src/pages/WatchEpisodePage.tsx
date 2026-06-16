import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  fetchEpisode,
  playEpisode,
  resolveManifestUrl,
} from "../api/client";
import { VideoPlayer } from "../components/VideoPlayer";

export function WatchEpisodePage() {
  const { episodeId } = useParams<{ episodeId: string }>();
  const navigate = useNavigate();
  const [src, setSrc] = useState<string | null>(null);
  const [subtitleUrl, setSubtitleUrl] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!episodeId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        let ep = await fetchEpisode(episodeId!);
        let manifest = resolveManifestUrl(ep.manifest_url);

        if (!manifest) {
          const playResult = await playEpisode(episodeId!);
          if (playResult.pipeline_status === "ready" && playResult.manifest_url) {
            manifest = resolveManifestUrl(playResult.manifest_url);
          } else if (playResult.pipeline_status === "transcoding") {
            for (let i = 0; i < 120; i++) {
              await new Promise((r) => setTimeout(r, 3000));
              ep = await fetchEpisode(episodeId!);
              manifest = resolveManifestUrl(ep.manifest_url);
              if (manifest) break;
            }
          } else if (playResult.pipeline_status === "failed") {
            throw new Error(
              playResult.message || "No se pudo preparar el episodio"
            );
          }
        }

        if (cancelled) return;

        if (!manifest) {
          if (!ep.has_local_media) {
            setError(
              "Este episodio no tiene archivo local. Abre la ficha de la serie para escanear la biblioteca."
            );
          } else {
            setError(
              "El episodio aún se está transcodificando. Vuelve a intentarlo en unos minutos."
            );
          }
          return;
        }

        setSrc(manifest);
        const epTitle = ep.title || `E${ep.episode_number}`;
        setTitle(`T${ep.season_number} · ${epTitle}`);
        if (ep.subtitle_path) {
          setSubtitleUrl(
            ep.subtitle_path.startsWith("/")
              ? ep.subtitle_path
              : `/${ep.subtitle_path}`
          );
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Error al cargar");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [episodeId]);

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p className="text-red-300">{error}</p>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-stream-accent"
        >
          Volver
        </button>
      </div>
    );
  }

  if (loading || !src) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-stream-muted">Cargando reproductor…</p>
      </div>
    );
  }

  return (
    <VideoPlayer
      src={src}
      title={title}
      episodeId={episodeId}
      subtitleUrl={subtitleUrl}
      onBack={() => navigate(-1)}
    />
  );
}
