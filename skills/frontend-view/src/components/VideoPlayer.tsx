import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";
import type { LiveDrmConfig } from "../api/types";

const WATCH_KEY_PREFIX = "watch:";

interface VideoPlayerProps {
  src: string;
  title?: string;
  episodeId?: string;
  watchKind?: "episode" | "movie";
  subtitleUrl?: string | null;
  live?: boolean;
  drm?: LiveDrmConfig | null;
  onBack?: () => void;
}

function watchStorageKey(episodeId: string): string {
  return `${WATCH_KEY_PREFIX}${episodeId}`;
}

function hlsErrorMessage(data: { type: string; details: string; fatal: boolean }): string {
  if (data.details === "manifestLoadError") {
    return "No se pudo cargar el manifiesto HLS. Comprueba la conexión o vuelve a intentarlo.";
  }
  if (data.details === "fragLoadError") {
    return "Error al cargar un segmento de vídeo. El stream puede estar caído o el archivo es demasiado grande.";
  }
  if (data.details === "bufferStalledError") {
    return "La reproducción se ha detenido por falta de datos. Espera o recarga la página.";
  }
  return `Error de reproducción (${data.details})`;
}

export function VideoPlayer({
  src,
  title,
  episodeId,
  watchKind = "episode",
  subtitleUrl,
  live = false,
  drm,
  onBack,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    let hls: Hls | null = null;
    setPlaybackError(null);

    if (episodeId) {
      const saved = localStorage.getItem(watchStorageKey(episodeId));
      if (saved) {
        try {
          const meta = JSON.parse(saved) as { position?: number };
          const position = meta.position ?? Number(saved);
          if (position > 5) video.currentTime = position;
        } catch {
          const position = Number(saved);
          if (position > 5) video.currentTime = position;
        }
      }
    }

    if (drm?.scheme === "widevine" && !window.navigator.requestMediaKeySystemAccess) {
      setPlaybackError(
        "Widevine DRM requiere Chrome o Edge. Safari y Firefox no son compatibles con BBC iPlayer."
      );
      return;
    }

    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: live,
        maxBufferLength: live ? 30 : 120,
        maxMaxBufferLength: live ? 60 : 600,
        fragLoadingTimeOut: live ? 20000 : 120000,
        manifestLoadingTimeOut: 20000,
        emeEnabled: Boolean(drm?.scheme === "widevine"),
        drmSystems:
          drm?.scheme === "widevine" && drm.license_proxy
            ? {
                "com.widevine.alpha": {
                  licenseUrl: drm.license_proxy,
                },
              }
            : undefined,
      });
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (!data.fatal) return;
        setPlaybackError(hlsErrorMessage(data));
        if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
          hls?.startLoad();
        } else {
          hls?.destroy();
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
      video.addEventListener("loadedmetadata", () => {
        video.play().catch(() => {});
      });
      video.addEventListener("error", () => {
        setPlaybackError("El navegador no pudo reproducir este stream.");
      });
    } else {
      setPlaybackError("Tu navegador no soporta reproducción HLS.");
    }

    const saveProgress = () => {
      if (!episodeId || video.currentTime < 5) return;
      const duration = video.duration && Number.isFinite(video.duration) ? video.duration : 0;
      if (duration > 0 && video.currentTime / duration > 0.95) {
        localStorage.removeItem(watchStorageKey(episodeId));
        return;
      }
      localStorage.setItem(
        watchStorageKey(episodeId),
        JSON.stringify({
          position: video.currentTime,
          duration,
          updatedAt: Date.now(),
          kind: watchKind,
        })
      );
    };

    video.addEventListener("timeupdate", saveProgress);

    return () => {
      video.removeEventListener("timeupdate", saveProgress);
      saveProgress();
      hls?.destroy();
    };
  }, [src, episodeId, live, watchKind, drm]);

  return (
    <div className="relative min-h-screen bg-black">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="absolute left-4 top-4 z-10 rounded bg-black/60 px-4 py-2 text-sm font-medium backdrop-blur transition hover:bg-black/80"
        >
          ← Volver
        </button>
      )}
      {title && (
        <h1 className="absolute left-4 top-16 z-10 max-w-lg text-lg font-bold drop-shadow-lg md:text-2xl">
          {title}
        </h1>
      )}
      {playbackError && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-4 bg-black/80 px-6 text-center">
          <p className="max-w-md text-red-300">{playbackError}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded bg-stream-accent px-4 py-2 text-sm font-medium text-white"
          >
            Reintentar
          </button>
        </div>
      )}
      <video
        ref={videoRef}
        className="h-screen w-full object-contain"
        controls
        playsInline
      >
        {subtitleUrl && (
          <track
            kind="subtitles"
            src={subtitleUrl}
            srcLang="es"
            label="Español"
            default
          />
        )}
      </video>
    </div>
  );
}
