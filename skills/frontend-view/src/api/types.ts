export interface CatalogItem {
  id: string;
  content_type: "movie" | "series" | string;
  origin: string;
  title: string;
  tags: string[];
  priority: number;
  notes?: string | null;
  tmdb_id?: number | null;
  year?: number | null;
  overview?: string | null;
  poster_url?: string | null;
  backdrop_url?: string | null;
  genres: string[];
  cast: string[];
  runtime_minutes?: number | null;
  tmdb_status?: string | null;
  magnet_status: string;
  pipeline_status: string;
  manifest_url?: string | null;
  ingest_mode?: string | null;
  error_message?: string | null;
}

export interface CatalogListResponse {
  items: CatalogItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface SeasonSummary {
  season_number: number;
  episode_count: number;
  ready_count: number;
  magnets_resolved: number;
}

export interface EpisodeItem {
  id: string;
  series_id: string;
  season_number: number;
  episode_number: number;
  title?: string | null;
  overview?: string | null;
  runtime_minutes?: number | null;
  magnet_status: string;
  pipeline_status: string;
  manifest_url?: string | null;
  ingest_mode?: string | null;
  error_message?: string | null;
  has_local_media?: boolean;
  still_url?: string | null;
  subtitle_path?: string | null;
}

export interface EpisodeListResponse {
  items: EpisodeItem[];
  total: number;
  season?: number | null;
}

export interface EpisodePlayResponse {
  episode_id: string;
  pipeline_status: string;
  manifest_url?: string | null;
  transcode_job_id?: string | null;
  message?: string | null;
  stage?: string | null;
  torrent_title?: string | null;
  torrent_size_gb?: number | null;
  seeders?: number | null;
}

export interface EpisodeAcquireResponse extends EpisodePlayResponse {}

export interface TitlePlayResponse {
  title_id: string;
  pipeline_status: string;
  manifest_url?: string | null;
  transcode_job_id?: string | null;
  message?: string | null;
}

export interface TitleStatusResponse {
  title_id: string;
  pipeline_status: string;
  manifest_url?: string | null;
  transcode_job_id?: string | null;
  error_message?: string | null;
}

export interface SystemStatus {
  acquire_ready: boolean;
  media_source_mode: string;
  checks: Record<string, boolean>;
  messages: string[];
  hints: Record<string, string>;
}

export interface CatalogStats {
  total: number;
  ready: number;
  cocteleria: number;
  failed: number;
}

export interface ActiveDownloadItem {
  id: string;
  series_id: string;
  season_number: number;
  episode_number: number;
  title?: string | null;
  pipeline_status: string;
}

export interface ActiveDownloadsResponse {
  items: ActiveDownloadItem[];
  total: number;
}

export interface LiveCountry {
  code: string;
  name: string;
  count: number;
}

export interface LiveChannel {
  id: string;
  name: string;
  group: string;
  country?: string | null;
  country_name?: string | null;
  region?: string | null;
  logo?: string | null;
  tags?: string[];
  drm?: string | null;
  requires_vpn?: boolean;
  geo_country?: string | null;
  auth_provider?: string | null;
}

export interface LiveDrmConfig {
  scheme: string;
  license_proxy: string;
}

export interface LiveStreamRequirements {
  vpn?: boolean;
  auth?: string;
  geo_country?: string;
}

export interface LiveChannelGroups {
  [group: string]: LiveChannel[];
}

export interface LiveChannelListResponse {
  groups: LiveChannelGroups;
  channels: LiveChannel[];
  countries: LiveCountry[];
  total: number;
}

export interface LiveStreamResponse {
  channel_id: string;
  name?: string;
  country?: string | null;
  country_name?: string | null;
  proxied_url: string;
  manifest_type?: string;
  drm?: LiveDrmConfig;
  requirements?: LiveStreamRequirements;
}

export interface LiveAuthStatus {
  bbc_configured: boolean;
  france_tv_configured: boolean;
  vpn_required: boolean;
  vpn_up: boolean;
}

export interface EpisodeStatusResponse {
  episode_id: string;
  pipeline_status: string;
  magnet_status: string;
  manifest_url?: string | null;
  transcode_job_id?: string | null;
  error_message?: string | null;
  stage?: string | null;
  message?: string | null;
  download_progress?: number | null;
  download_speed_mbps?: number | null;
}

export interface CocktailItem {
  id: string;
  title_id: string;
  name: string;
  ingredients: string[];
  recipe: string[];
  timestamp_seconds?: number | null;
  scene?: string | null;
}
