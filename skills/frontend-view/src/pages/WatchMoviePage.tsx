import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchTitle, resolveManifestUrl } from "../api/client";
import { VideoPlayer } from "../components/VideoPlayer";

export function WatchMoviePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [src, setSrc] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchTitle(id)
      .then((item) => {
        const manifest = resolveManifestUrl(item.manifest_url);
        if (!manifest) {
          setError("Esta película aún no está lista para reproducir.");
          return;
        }
        setSrc(manifest);
        setTitle(item.title);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Error al cargar");
      });
  }, [id]);

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

  if (!src) {
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
      episodeId={id}
      watchKind="movie"
      onBack={() => navigate(-1)}
    />
  );
}
