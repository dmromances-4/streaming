import { useEffect, useState } from "react";
import { fetchActiveDownloads, fetchLiveAuthStatus, fetchSystemStatus } from "../api/client";
import type { ActiveDownloadItem, LiveAuthStatus, SystemStatus } from "../api/types";

export function SettingsPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [downloads, setDownloads] = useState<ActiveDownloadItem[]>([]);
  const [liveAuth, setLiveAuth] = useState<LiveAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchSystemStatus(), fetchActiveDownloads(), fetchLiveAuthStatus()])
      .then(([s, d, live]) => {
        setStatus(s);
        setDownloads(d.items);
        setLiveAuth(live);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10 text-stream-muted">
        Cargando ajustes…
      </div>
    );
  }

  const checks = status?.checks ?? {};

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 md:px-10">
      <h1 className="mb-6 text-2xl font-bold">Ajustes del sistema</h1>

      <section className="mb-8 rounded-xl border border-stream-border bg-stream-surface p-6">
        <h2 className="mb-4 text-lg font-semibold">Descargas torrent</h2>
        <p className="mb-4 text-sm text-stream-muted">
          Modo actual: <strong>{status?.media_source_mode}</strong>
          {status?.acquire_ready ? (
            <span className="ml-2 text-emerald-400">· Listo para descargar</span>
          ) : (
            <span className="ml-2 text-amber-400">· Configuración incompleta</span>
          )}
        </p>
        <ul className="space-y-3">
          <CheckItem
            ok={checks.indexer_configured}
            label="INDEXER_API_KEY en .env"
            hint="Prowlarr → Settings → General"
          />
          <CheckItem
            ok={checks.indexer_reachable}
            label="Prowlarr con indexers activos"
            hint={status?.hints.prowlarr_url}
          />
          <CheckItem
            ok={checks.qbittorrent_ok}
            label="qBittorrent accesible"
            hint={status?.hints.qbittorrent_url}
          />
          <CheckItem
            ok={checks.media_path_ok}
            label="Carpeta de biblioteca montada (/downloads)"
            hint="MEDIA_HOST_PATH en .env"
          />
        </ul>
        {(status?.messages?.length ?? 0) > 0 && (
          <ul className="mt-4 space-y-2 text-sm text-amber-200">
            {status!.messages.map((m) => (
              <li key={m}>• {m}</li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-stream-muted">
          Ejecuta: <code className="text-white/80">bash deploy/scripts/setup-prowlarr.sh</code>
        </p>
      </section>

      {downloads.length > 0 && (
        <section className="rounded-xl border border-stream-border bg-stream-surface p-6">
          <h2 className="mb-4 text-lg font-semibold">Actividad de descarga</h2>
          <ul className="space-y-2 text-sm">
            {downloads.map((d) => (
              <li key={d.id} className="flex justify-between gap-4">
                <span>
                  S{d.season_number}E{d.episode_number}
                  {d.title ? ` · ${d.title}` : ""}
                </span>
                <span className="text-stream-muted">{d.pipeline_status}</span>
              </li>
            ))}
          </ul>
          <a
            href="http://localhost:8080"
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-block text-sm text-stream-accent hover:underline"
          >
            Abrir qBittorrent Web UI →
          </a>
        </section>
      )}

      <section className="mt-8 rounded-xl border border-stream-border bg-stream-surface p-6">
        <h2 className="mb-4 text-lg font-semibold">TV en directo</h2>
        <ul className="mb-4 space-y-3">
          <CheckItem
            ok={liveAuth?.vpn_up ?? !liveAuth?.vpn_required}
            label={
              liveAuth?.vpn_required
                ? "VPN UK activa (live-sports)"
                : "VPN no requerida para TV en directo"
            }
            hint="docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.vpn.yml up -d"
          />
          <CheckItem
            ok={liveAuth?.bbc_configured}
            label="BBC_IPLAYER_COOKIES en .env"
            hint="Exporta cookies de bbc.co.uk tras iniciar sesión en iPlayer"
          />
          <CheckItem
            ok={liveAuth?.france_tv_configured ?? true}
            label="FRANCE_TV_COOKIES (opcional)"
            hint="Solo si France.tv devuelve error de autenticación"
          />
        </ul>
        <div className="space-y-2 text-sm text-stream-muted">
          <p>
            <strong>BBC iPlayer</strong> (BBC One, Two, Three, Four) usa Widevine DRM.
            Reproduce en Chrome o Edge con VPN UK y cookies válidas.
          </p>
          <p>
            Añade en <code className="text-white/80">deploy/.env</code>:
          </p>
          <pre className="overflow-x-auto rounded bg-black/40 p-3 text-xs text-white/90">
{`BBC_IPLAYER_COOKIES="BBC-UID=...; ckns_policy=...; ..."
WIREGUARD_PRIVATE_KEY=...  # overlay VPN UK`}
          </pre>
          <p className="text-xs">
            Debes tener TV License UK válida. Las cookies caducan — renueva periódicamente.
          </p>
        </div>
      </section>
    </div>
  );
}

function CheckItem({
  ok,
  label,
  hint,
}: {
  ok?: boolean;
  label: string;
  hint?: string;
}) {
  return (
    <li className="flex items-start gap-3 text-sm">
      <span className={ok ? "text-emerald-400" : "text-red-400"}>
        {ok ? "✓" : "✗"}
      </span>
      <div>
        <p>{label}</p>
        {hint && <p className="text-xs text-stream-muted">{hint}</p>}
      </div>
    </li>
  );
}
