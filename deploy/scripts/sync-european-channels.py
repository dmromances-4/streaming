#!/usr/bin/env python3
"""Genera YAML de canales públicos europeos por país."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("pip install pyyaml", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "catalog" / "data" / "live-channels"

LOGO = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries"

# Curated public service broadcasters (HLS where known stable).
CHANNELS: list[dict] = [
    # --- España (RTVE dynamic) ---
    {"id": "rtve-la1", "name": "La 1", "country": "ES", "group": "Generalista", "resolver": "rtve", "slug": "la-1", "logo": "https://www.rtve.es/favicon.ico"},
    {"id": "rtve-la2", "name": "La 2", "country": "ES", "group": "Generalista", "resolver": "rtve", "slug": "la-2", "logo": "https://www.rtve.es/favicon.ico"},
    {"id": "rtve-24h", "name": "24 Horas", "country": "ES", "group": "Noticias", "resolver": "rtve", "slug": "24h", "logo": "https://www.rtve.es/favicon.ico"},
    {"id": "rtve-tdp", "name": "Teledeporte", "country": "ES", "group": "Deportes", "resolver": "rtve", "slug": "tdp", "logo": "https://www.rtve.es/favicon.ico"},
    {"id": "rtve-clan", "name": "Clan", "country": "ES", "group": "Infantil", "resolver": "rtve", "slug": "clan", "logo": "https://www.rtve.es/favicon.ico"},
    {"id": "rtve-teledeporte-youth", "name": "Clan TVE", "country": "ES", "group": "Infantil", "resolver": "rtve", "slug": "clan", "logo": "https://www.rtve.es/favicon.ico", "enabled": False},
    # --- España (TV autonómicas) ---
    {"id": "es-ccma-tv3", "name": "TV3", "country": "ES", "group": "Autonómica · Cataluña", "region": "Cataluña", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ccma", "ccma_id": "tv3", "logo": "https://statics.3cat.cat/img/logos/tv3_colorBgNegre.svg"},
    {"id": "es-ccma-324", "name": "3/24", "country": "ES", "group": "Autonómica · Cataluña", "region": "Cataluña", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ccma", "ccma_id": "324", "logo": "https://statics.3cat.cat/img/logos/tv3_colorBgNegre.svg"},
    {"id": "es-ccma-esport3", "name": "Esport3", "country": "ES", "group": "Autonómica · Cataluña", "region": "Cataluña", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ccma", "ccma_id": "esport3", "logo": "https://statics.3cat.cat/img/logos/tv3_colorBgNegre.svg"},
    {"id": "es-ccma-super3", "name": "SX3", "country": "ES", "group": "Autonómica · Cataluña", "region": "Cataluña", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ccma", "ccma_id": "super3", "logo": "https://statics.3cat.cat/img/logos/tv3_colorBgNegre.svg"},
    {"id": "es-ccma-33", "name": "El 33", "country": "ES", "group": "Autonómica · Cataluña", "region": "Cataluña", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ccma", "ccma_id": "33", "logo": "https://statics.3cat.cat/img/logos/tv3_colorBgNegre.svg"},
    {"id": "es-ccma-tv3cat", "name": "TV3CAT", "country": "ES", "group": "Autonómica · Cataluña", "region": "Cataluña", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ccma", "ccma_id": "tvc", "logo": "https://statics.3cat.cat/img/logos/tv3_colorBgNegre.svg"},
    {"id": "es-etb1", "name": "ETB 1", "country": "ES", "group": "Autonómica · País Vasco", "region": "País Vasco", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://multimedia.eitb.eus/live-content/etb1hd-hls/master.m3u8", "logo": "https://www.eitb.eus/favicon.ico"},
    {"id": "es-etb2", "name": "ETB 2", "country": "ES", "group": "Autonómica · País Vasco", "region": "País Vasco", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://multimedia.eitb.eus/live-content/etb2hd-hls/master.m3u8", "logo": "https://www.eitb.eus/favicon.ico"},
    {"id": "es-etb-basque", "name": "ETB Basque", "country": "ES", "group": "Autonómica · País Vasco", "region": "País Vasco", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://multimedia.eitb.eus/live-content/eitbbasque-hls/master.m3u8", "logo": "https://www.eitb.eus/favicon.ico"},
    {"id": "es-csur-andalucia", "name": "Canal Sur", "country": "ES", "group": "Autonómica · Andalucía", "region": "Andalucía", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://dfk2a268yviz9.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-ddiii1m6jt6of/CanalSurAndaluciaES.m3u8", "logo": "https://www.canalsur.es/favicon.ico"},
    {"id": "es-csur-2", "name": "Canal Sur 2", "country": "ES", "group": "Autonómica · Andalucía", "region": "Andalucía", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://cdnlive.codev8.net/rtvalive/smil:channel22.smil/playlist.m3u8", "logo": "https://www.canalsur.es/favicon.ico"},
    {"id": "es-csur-noticias", "name": "Canal Sur Noticias", "country": "ES", "group": "Autonómica · Andalucía", "region": "Andalucía", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://cdnlive.codev8.net/rtvalive/smil:channel42.smil/playlist.m3u8", "logo": "https://www.canalsur.es/favicon.ico"},
    {"id": "es-telemadrid", "name": "Telemadrid", "country": "ES", "group": "Autonómica · Madrid", "region": "Madrid", "tags": ["autonomic"], "geo_country": "ES", "resolver": "brightcove", "brightcove_account": "6416060453001", "brightcove_ref": "Live_Telemadrid", "brightcove_player": "2rfYSrHC79", "logo": "https://www.telemadrid.es/favicon.ico", "proxy_headers": {"Referer": "https://www.telemadrid.es/", "Origin": "https://www.telemadrid.es"}},
    {"id": "es-telemadrid-laotra", "name": "La Otra", "country": "ES", "group": "Autonómica · Madrid", "region": "Madrid", "tags": ["autonomic"], "geo_country": "ES", "resolver": "brightcove", "brightcove_account": "6416060453001", "brightcove_ref": "Live_LaOtra", "brightcove_player": "2rfYSrHC79", "logo": "https://www.telemadrid.es/favicon.ico", "proxy_headers": {"Referer": "https://www.telemadrid.es/", "Origin": "https://www.telemadrid.es"}},
    {"id": "es-apunt", "name": "À Punt", "country": "ES", "group": "Autonómica · Comunitat Valenciana", "region": "Comunitat Valenciana", "tags": ["autonomic"], "geo_country": "ES", "resolver": "brightcove", "brightcove_account": "6057955885001", "brightcove_ref": "1846756479408303045", "brightcove_player": "91QJ7lbqkj", "logo": "https://www.apuntmedia.es/favicon.ico", "proxy_headers": {"Referer": "https://www.apuntmedia.es/", "Origin": "https://www.apuntmedia.es"}},
    {"id": "es-aragon-tv", "name": "Aragón TV", "country": "ES", "group": "Autonómica · Aragón", "region": "Aragón", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://cartv.streaming.aranova.es/hls/live/aragontv_canal1.m3u8", "logo": "https://www.aragontelevision.es/favicon.ico"},
    {"id": "es-canal-extremadura", "name": "Canal Extremadura", "country": "ES", "group": "Autonómica · Extremadura", "region": "Extremadura", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://canalextremadura-live.flumotion.cloud/canalextremadura/live_all/playlist.m3u8", "logo": "https://www.canalextremadura.es/favicon.ico"},
    {"id": "es-rioja-tv", "name": "Rioja Televisión", "country": "ES", "group": "Autonómica · La Rioja", "region": "La Rioja", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://5924d3ad0efcf.streamlock.net/riojatv/riojatvlive/playlist.m3u8", "logo": "https://www.larioja.org/favicon.ico", "proxy_headers": {"Referer": "https://www.larioja.org/", "Origin": "https://www.larioja.org"}, "enabled": False},
    {"id": "es-tvg", "name": "TVG", "country": "ES", "group": "Autonómica · Galicia", "region": "Galicia", "tags": ["autonomic"], "geo_country": "ES", "resolver": "tvg", "logo": "https://www.crtvg.es/favicon.ico"},
    {"id": "es-tvg2", "name": "TVG2", "country": "ES", "group": "Autonómica · Galicia", "region": "Galicia", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://crtvg-tvg2.flumotion.cloud/playlist.m3u8", "logo": "https://www.crtvg.es/favicon.ico"},
    {"id": "es-lancelot", "name": "TV Canaria", "country": "ES", "group": "Autonómica · Canarias", "region": "Canarias", "tags": ["autonomic"], "geo_country": "ES", "resolver": "static", "stream_url": "https://5c0956165db0b.streamlock.net:8090/directo/_definst_/lancelot.television/master.m3u8", "logo": "https://www.lancelot.tv/favicon.ico"},
    {"id": "es-cyl-la7", "name": "La 7", "country": "ES", "group": "Autonómica · Castilla y León", "region": "Castilla y León", "tags": ["autonomic"], "geo_country": "ES", "resolver": "cyltv", "cyltv_slug": "la7", "logo": "https://www.cyltv.es/favicon.ico"},
    {"id": "es-ib3", "name": "IB3", "country": "ES", "group": "Autonómica · Illes Balears", "region": "Illes Balears", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ib3", "ib3_slug": "televisio", "logo": "https://ib3.org/favicon.ico", "enabled": False},
    {"id": "es-ib3-2", "name": "IB3 2", "country": "ES", "group": "Autonómica · Illes Balears", "region": "Illes Balears", "tags": ["autonomic"], "geo_country": "ES", "resolver": "ib3", "ib3_slug": "2", "logo": "https://ib3.org/favicon.ico", "enabled": False},
    {"id": "es-7rm", "name": "7 Región de Murcia", "country": "ES", "group": "Autonómica · Murcia", "region": "Murcia", "tags": ["autonomic"], "geo_country": "ES", "resolver": "murcia", "logo": "https://www.7tvregiondemurcia.es/favicon.ico"},
    {"id": "es-navarra-tv", "name": "Navarra Televisión", "country": "ES", "group": "Autonómica · Navarra", "region": "Navarra", "tags": ["autonomic"], "geo_country": "ES", "resolver": "navarra", "page_url": "https://www.natvplay.es/player/navarra-television/navarra-television-live", "logo": "https://www.navarratelevision.es/favicon.ico"},
    {"id": "es-tpa", "name": "TPA", "country": "ES", "group": "Autonómica · Asturias", "region": "Asturias", "tags": ["autonomic"], "geo_country": "ES", "resolver": "tpa", "logo": "https://www.rtpa.es/favicon.ico"},
    {"id": "es-trc", "name": "Televisión de Cantabria", "country": "ES", "group": "Autonómica · Cantabria", "region": "Cantabria", "tags": ["autonomic"], "geo_country": "ES", "resolver": "trc", "logo": "https://www.tvcantabria.es/favicon.ico"},
    {"id": "es-clm-cmt", "name": "Castilla-La Mancha Media", "country": "ES", "group": "Autonómica · Castilla-La Mancha", "region": "Castilla-La Mancha", "tags": ["autonomic"], "geo_country": "ES", "resolver": "clm", "logo": "https://www.cmmedia.es/favicon.ico"},
    # --- Alemania ---
    {"id": "de-daserste", "name": "Das Erste", "country": "DE", "group": "Generalista", "resolver": "static", "stream_url": "https://daserste-live.ard-mcdn.de/daserste/live/hls/de/master.m3u8"},
    {"id": "de-zdf", "name": "ZDF", "country": "DE", "group": "Generalista", "resolver": "static", "stream_url": "https://zdf-hls-15.akamaized.net/hls/live/2016498/de/high/master.m3u8"},
    {"id": "de-zdfneo", "name": "ZDFneo", "country": "DE", "group": "Temático", "resolver": "static", "stream_url": "https://zdf-hls-16.akamaized.net/hls/live/2016499/de/high/master.m3u8"},
    {"id": "de-zdfinfo", "name": "ZDFinfo", "country": "DE", "group": "Noticias", "resolver": "static", "stream_url": "https://zdf-hls-17.akamaized.net/hls/live/2016500/de/high/master.m3u8"},
    {"id": "de-3sat", "name": "3sat", "country": "DE", "group": "Cultura", "resolver": "static", "stream_url": "https://zdf-hls-18.akamaized.net/hls/live/2016501/dach/high/master.m3u8"},
    {"id": "de-phoenix", "name": "Phoenix", "country": "DE", "group": "Noticias", "resolver": "static", "stream_url": "https://zdf-hls-19.akamaized.net/hls/live/2016502/de/high/master.m3u8"},
    {"id": "de-arte-de", "name": "ARTE Deutsch", "country": "DE", "group": "Cultura", "resolver": "static", "stream_url": "https://artesimulcast.akamaized.net/hls/live/2030993/artelive_de/master.m3u8"},
    {"id": "de-kika", "name": "KiKA", "country": "DE", "group": "Infantil", "resolver": "static", "stream_url": "https://kikade-live.ard-mcdn.de/kika/live/hls/de/master.m3u8"},
    {"id": "de-br", "name": "BR Fernsehen", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://mcdn.br.de/br/fs/br/hls/de/master.m3u8"},
    {"id": "de-wdr", "name": "WDR", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://wdr-live.ard-mcdn.de/wdr/live/hls/de/master.m3u8"},
    {"id": "de-ndr", "name": "NDR", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://ndr-live.ard-mcdn.de/ndr/live/hls/de/master.m3u8"},
    {"id": "de-mdr", "name": "MDR", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://mdr-live.ard-mcdn.de/mdr/live/hls/de/master.m3u8"},
    {"id": "de-swr", "name": "SWR", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://swr-live.ard-mcdn.de/swr/live/hls/de/master.m3u8"},
    {"id": "de-rbb", "name": "RBB", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://rbb-live.ard-mcdn.de/rbb/live/hls/de/master.m3u8"},
    {"id": "de-hr", "name": "HR", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://hr-live.ard-mcdn.de/hr/live/hls/de/master.m3u8"},
    {"id": "de-sr", "name": "SR", "country": "DE", "group": "Regional", "resolver": "static", "stream_url": "https://sr-live.ard-mcdn.de/sr/live/hls/de/master.m3u8"},
    {"id": "de-dw", "name": "Deutsche Welle", "country": "DE", "group": "Internacional", "resolver": "static", "stream_url": "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8"},
    # --- Francia ---
    {"id": "fr-arte-fr", "name": "ARTE Français", "country": "FR", "group": "Cultura", "resolver": "static", "stream_url": "https://artesimulcast.akamaized.net/hls/live/2031003/artelive_fr/master.m3u8"},
    {"id": "fr-france2", "name": "France 2", "country": "FR", "group": "Generalista", "resolver": "france_tv", "channel_uuid": "SIMULCAST_FRANCE2"},
    {"id": "fr-france3", "name": "France 3", "country": "FR", "group": "Generalista", "resolver": "france_tv", "channel_uuid": "SIMULCAST_FRANCE3"},
    {"id": "fr-france5", "name": "France 5", "country": "FR", "group": "Cultura", "resolver": "france_tv", "channel_uuid": "SIMULCAST_FRANCE5"},
    {"id": "fr-franceinfo", "name": "franceinfo", "country": "FR", "group": "Noticias", "resolver": "france_tv", "channel_uuid": "SIMULCAST_FRANCEINFO"},
    {"id": "fr-lcp", "name": "LCP", "country": "FR", "group": "Parlamento", "resolver": "france_tv", "channel_uuid": "SIMULCAST_LCP"},
    {"id": "fr-public-senat", "name": "Public Sénat", "country": "FR", "group": "Parlamento", "resolver": "france_tv", "channel_uuid": "SIMULCAST_PUBLIC_SENAT"},
    # --- Italia ---
    {"id": "it-rai1", "name": "Rai 1", "country": "IT", "group": "Generalista", "resolver": "rai", "slug": "rai-1"},
    {"id": "it-rai2", "name": "Rai 2", "country": "IT", "group": "Generalista", "resolver": "rai", "slug": "rai-2"},
    {"id": "it-rai3", "name": "Rai 3", "country": "IT", "group": "Generalista", "resolver": "rai", "slug": "rai-3"},
    {"id": "it-rainews24", "name": "Rai News 24", "country": "IT", "group": "Noticias", "resolver": "rai", "slug": "rainews24"},
    {"id": "it-raisport", "name": "Rai Sport", "country": "IT", "group": "Deportes", "resolver": "rai", "slug": "raisport"},
    {"id": "it-raiscuola", "name": "Rai Scuola", "country": "IT", "group": "Cultura", "resolver": "rai", "slug": "raiscuola"},
    {"id": "it-raistoria", "name": "Rai Storia", "country": "IT", "group": "Cultura", "resolver": "rai", "slug": "raistoria"},
    # --- Portugal ---
    {"id": "pt-rtp1", "name": "RTP 1", "country": "PT", "group": "Generalista", "resolver": "static", "stream_url": "https://streaming-live.rtp.pt/live/rtp1/rtp1.m3u8"},
    {"id": "pt-rtp2", "name": "RTP 2", "country": "PT", "group": "Generalista", "resolver": "static", "stream_url": "https://streaming-live.rtp.pt/live/rtp2/rtp2.m3u8"},
    {"id": "pt-rtp3", "name": "RTP 3", "country": "PT", "group": "Noticias", "resolver": "static", "stream_url": "https://streaming-live.rtp.pt/live/rtp3/rtp3.m3u8"},
    {"id": "pt-rtpmemoria", "name": "RTP Memória", "country": "PT", "group": "Cultura", "resolver": "static", "stream_url": "https://streaming-live.rtp.pt/live/rtpmemoria/rtpmemoria.m3u8"},
    {"id": "pt-rtpazores", "name": "RTP Açores", "country": "PT", "group": "Regional", "resolver": "static", "stream_url": "https://streaming-live.rtp.pt/live/rtpacores/rtpacores.m3u8"},
    {"id": "pt-rtpmadeira", "name": "RTP Madeira", "country": "PT", "group": "Regional", "resolver": "static", "stream_url": "https://streaming-live.rtp.pt/live/rtpmadeira/rtpmadeira.m3u8"},
    # --- Países Bajos ---
    {"id": "nl-npo1", "name": "NPO 1", "country": "NL", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/npo1/browser-HLS8/npo1.m3u8"},
    {"id": "nl-npo2", "name": "NPO 2", "country": "NL", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/npo2/browser-HLS8/npo2.m3u8"},
    {"id": "nl-npo3", "name": "NPO 3", "country": "NL", "group": "Temático", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/npo3/browser-HLS8/npo3.m3u8"},
    {"id": "nl-npopolitiek", "name": "NPO Politiek", "country": "NL", "group": "Parlamento", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/npopolitiek/browser-HLS8/npopolitiek.m3u8"},
    # --- Bélgica ---
    {"id": "be-vrt1", "name": "VRT 1", "country": "BE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/vrt1/browser-HLS8/vrt1.m3u8"},
    {"id": "be-canvas", "name": "Canvas", "country": "BE", "group": "Cultura", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/canvas/browser-HLS8/canvas.m3u8"},
    {"id": "be-ketnet", "name": "Ketnet", "country": "BE", "group": "Infantil", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ketnet/browser-HLS8/ketnet.m3u8"},
    {"id": "be-laune", "name": "La Une", "country": "BE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/laune/browser-HLS8/laune.m3u8"},
    {"id": "be-ladeux", "name": "La Deux", "country": "BE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ladeux/browser-HLS8/ladeux.m3u8"},
    # --- Austria ---
    {"id": "at-orf1", "name": "ORF 1", "country": "AT", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/orf1/browser-HLS8/orf1.m3u8"},
    {"id": "at-orf2", "name": "ORF 2", "country": "AT", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/orf2/browser-HLS8/orf2.m3u8"},
    {"id": "at-orf3", "name": "ORF III", "country": "AT", "group": "Cultura", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/orf3/browser-HLS8/orf3.m3u8"},
    {"id": "at-3sat", "name": "3sat", "country": "AT", "group": "Cultura", "resolver": "static", "stream_url": "https://zdf-hls-18.akamaized.net/hls/live/2016501/dach/high/master.m3u8"},
    # --- Suiza ---
    {"id": "ch-srf1", "name": "SRF 1", "country": "CH", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/srf1/browser-HLS8/srf1.m3u8"},
    {"id": "ch-srf2", "name": "SRF 2", "country": "CH", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/srf2/browser-HLS8/srf2.m3u8"},
    {"id": "ch-rsi", "name": "RSI La 1", "country": "CH", "group": "Regional", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rsila1/browser-HLS8/rsila1.m3u8"},
    {"id": "ch-rts1", "name": "RTS Un", "country": "CH", "group": "Regional", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rtsun/browser-HLS8/rtsun.m3u8"},
    # --- Reino Unido ---
    {"id": "uk-bbcone", "name": "BBC One", "country": "GB", "group": "Generalista", "resolver": "bbc_iplayer", "vpid": "bbc_one", "requires_vpn": True, "geo_country": "GB", "auth_provider": "bbc", "drm": "widevine"},
    {"id": "uk-bbctwo", "name": "BBC Two", "country": "GB", "group": "Generalista", "resolver": "bbc_iplayer", "vpid": "bbc_two", "requires_vpn": True, "geo_country": "GB", "auth_provider": "bbc", "drm": "widevine"},
    {"id": "uk-bbcthree", "name": "BBC Three", "country": "GB", "group": "Temático", "resolver": "bbc_iplayer", "vpid": "bbc_three", "requires_vpn": True, "geo_country": "GB", "auth_provider": "bbc", "drm": "widevine"},
    {"id": "uk-bbcfour", "name": "BBC Four", "country": "GB", "group": "Cultura", "resolver": "bbc_iplayer", "vpid": "bbc_four", "requires_vpn": True, "geo_country": "GB", "auth_provider": "bbc", "drm": "widevine"},
    {"id": "uk-cbbc", "name": "CBBC", "country": "GB", "group": "Infantil", "resolver": "bbc_iplayer", "vpid": "cbbc", "requires_vpn": True, "geo_country": "GB", "auth_provider": "bbc", "drm": "widevine"},
    {"id": "uk-cbeebies", "name": "CBeebies", "country": "GB", "group": "Infantil", "resolver": "bbc_iplayer", "vpid": "cbeebies", "requires_vpn": True, "geo_country": "GB", "auth_provider": "bbc", "drm": "widevine"},
    {"id": "uk-bbcnews", "name": "BBC News", "country": "GB", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/bbcnews/browser-HLS8/bbcnews.m3u8"},
    {"id": "uk-bbcparliament", "name": "BBC Parliament", "country": "GB", "group": "Parlamento", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/bbcparliament/browser-HLS8/bbcparliament.m3u8"},
    {"id": "uk-channel4", "name": "Channel 4", "country": "GB", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/channel4/browser-HLS8/channel4.m3u8"},
    {"id": "uk-channel5", "name": "Channel 5", "country": "GB", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/channel5/browser-HLS8/channel5.m3u8"},
    # --- Irlanda ---
    {"id": "ie-rte1", "name": "RTÉ One", "country": "IE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rte1/browser-HLS8/rte1.m3u8"},
    {"id": "ie-rte2", "name": "RTÉ2", "country": "IE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rte2/browser-HLS8/rte2.m3u8"},
    {"id": "ie-rtenews", "name": "RTÉ News", "country": "IE", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rtenews/browser-HLS8/rtenews.m3u8"},
    # --- Nórdicos ---
    {"id": "no-nrk1", "name": "NRK1", "country": "NO", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/nrk1/browser-HLS8/nrk1.m3u8"},
    {"id": "no-nrk2", "name": "NRK2", "country": "NO", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/nrk2/browser-HLS8/nrk2.m3u8"},
    {"id": "no-nrk3", "name": "NRK3", "country": "NO", "group": "Temático", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/nrk3/browser-HLS8/nrk3.m3u8"},
    {"id": "no-nrksuper", "name": "NRK Super", "country": "NO", "group": "Infantil", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/nrksuper/browser-HLS8/nrksuper.m3u8"},
    {"id": "se-svt1", "name": "SVT 1", "country": "SE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/svt1/browser-HLS8/svt1.m3u8"},
    {"id": "se-svt2", "name": "SVT 2", "country": "SE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/svt2/browser-HLS8/svt2.m3u8"},
    {"id": "se-svtbarn", "name": "SVT Barn", "country": "SE", "group": "Infantil", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/svtbarn/browser-HLS8/svtbarn.m3u8"},
    {"id": "se-kunskapskanalen", "name": "Kunskapskanalen", "country": "SE", "group": "Cultura", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/kunskapskanalen/browser-HLS8/kunskapskanalen.m3u8"},
    {"id": "dk-dr1", "name": "DR1", "country": "DK", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/dr1/browser-HLS8/dr1.m3u8"},
    {"id": "dk-dr2", "name": "DR2", "country": "DK", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/dr2/browser-HLS8/dr2.m3u8"},
    {"id": "dk-dr-ramasjang", "name": "DR Ramasjang", "country": "DK", "group": "Infantil", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/drramasjang/browser-HLS8/drramasjang.m3u8"},
    {"id": "fi-yle1", "name": "Yle TV1", "country": "FI", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/yletv1/browser-HLS8/yletv1.m3u8"},
    {"id": "fi-yle2", "name": "Yle TV2", "country": "FI", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/yletv2/browser-HLS8/yletv2.m3u8"},
    {"id": "fi-yleteema", "name": "Yle Teema", "country": "FI", "group": "Cultura", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/yleteema/browser-HLS8/yleteema.m3u8"},
    {"id": "is-ruv", "name": "RÚV", "country": "IS", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ruv/browser-HLS8/ruv.m3u8"},
    # --- Europa del Este ---
    {"id": "pl-tvp1", "name": "TVP 1", "country": "PL", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvp1/browser-HLS8/tvp1.m3u8"},
    {"id": "pl-tvp2", "name": "TVP 2", "country": "PL", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvp2/browser-HLS8/tvp2.m3u8"},
    {"id": "pl-tvpinfo", "name": "TVP Info", "country": "PL", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvpinfo/browser-HLS8/tvpinfo.m3u8"},
    {"id": "cz-ct1", "name": "ČT1", "country": "CZ", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ct1/browser-HLS8/ct1.m3u8"},
    {"id": "cz-ct2", "name": "ČT2", "country": "CZ", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ct2/browser-HLS8/ct2.m3u8"},
    {"id": "cz-ct24", "name": "ČT24", "country": "CZ", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ct24/browser-HLS8/ct24.m3u8"},
    {"id": "sk-stv1", "name": "STV1", "country": "SK", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/stv1/browser-HLS8/stv1.m3u8"},
    {"id": "sk-stv2", "name": "STV2", "country": "SK", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/stv2/browser-HLS8/stv2.m3u8"},
    {"id": "hu-m1", "name": "M1", "country": "HU", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/m1/browser-HLS8/m1.m3u8"},
    {"id": "hu-m2", "name": "M2", "country": "HU", "group": "Infantil", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/m2/browser-HLS8/m2.m3u8"},
    {"id": "hu-m4", "name": "M4 Sport", "country": "HU", "group": "Deportes", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/m4sport/browser-HLS8/m4sport.m3u8"},
    {"id": "ro-tvr1", "name": "TVR 1", "country": "RO", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvr1/browser-HLS8/tvr1.m3u8"},
    {"id": "ro-tvr2", "name": "TVR 2", "country": "RO", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvr2/browser-HLS8/tvr2.m3u8"},
    {"id": "ro-tvr3", "name": "TVR 3", "country": "RO", "group": "Regional", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvr3/browser-HLS8/tvr3.m3u8"},
    {"id": "bg-bnt1", "name": "BNT 1", "country": "BG", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/bnt1/browser-HLS8/bnt1.m3u8"},
    {"id": "bg-bnt2", "name": "BNT 2", "country": "BG", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/bnt2/browser-HLS8/bnt2.m3u8"},
    {"id": "gr-ert1", "name": "ERT 1", "country": "GR", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ert1/browser-HLS8/ert1.m3u8"},
    {"id": "gr-ert2", "name": "ERT 2", "country": "GR", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ert2/browser-HLS8/ert2.m3u8"},
    {"id": "gr-ertnews", "name": "ERT News", "country": "GR", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ertnews/browser-HLS8/ertnews.m3u8"},
    {"id": "hr-hrt1", "name": "HRT 1", "country": "HR", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/hrt1/browser-HLS8/hrt1.m3u8"},
    {"id": "hr-hrt2", "name": "HRT 2", "country": "HR", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/hrt2/browser-HLS8/hrt2.m3u8"},
    {"id": "hr-hrt3", "name": "HRT 3", "country": "HR", "group": "Cultura", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/hrt3/browser-HLS8/hrt3.m3u8"},
    {"id": "si-rtvslo1", "name": "RTV SLO 1", "country": "SI", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rtvslo1/browser-HLS8/rtvslo1.m3u8"},
    {"id": "si-rtvslo2", "name": "RTV SLO 2", "country": "SI", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rtvslo2/browser-HLS8/rtvslo2.m3u8"},
    {"id": "ee-err", "name": "ETV", "country": "EE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/etv/browser-HLS8/etv.m3u8"},
    {"id": "ee-err2", "name": "ETV2", "country": "EE", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/etv2/browser-HLS8/etv2.m3u8"},
    {"id": "lv-ltv1", "name": "LTV1", "country": "LV", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ltv1/browser-HLS8/ltv1.m3u8"},
    {"id": "lv-ltv7", "name": "LTV7", "country": "LV", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/ltv7/browser-HLS8/ltv7.m3u8"},
    {"id": "lt-lrt", "name": "LRT", "country": "LT", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/lrt/browser-HLS8/lrt.m3u8"},
    {"id": "lt-lrtplius", "name": "LRT Plius", "country": "LT", "group": "Cultura", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/lrtplius/browser-HLS8/lrtplius.m3u8"},
    # --- Pequeños estados ---
    {"id": "lu-rtl", "name": "RTL Télé Lëtzebuerg", "country": "LU", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rtltele/browser-HLS8/rtltele.m3u8"},
    {"id": "mt-tvm", "name": "TVM", "country": "MT", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/tvm/browser-HLS8/tvm.m3u8"},
    {"id": "cy-rik", "name": "RIK 1", "country": "CY", "group": "Generalista", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/rik1/browser-HLS8/rik1.m3u8"},
    # --- Pan-europeos ---
    {"id": "eu-euronews", "name": "Euronews", "country": "EU", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/euronews/browser-HLS8/euronews.m3u8"},
    {"id": "eu-euronews-en", "name": "Euronews English", "country": "EU", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/euronewsen/browser-HLS8/euronewsen.m3u8"},
    {"id": "eu-france24-en", "name": "France 24 English", "country": "EU", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/france24en/browser-HLS8/france24en.m3u8"},
    {"id": "eu-france24-fr", "name": "France 24 Français", "country": "EU", "group": "Noticias", "resolver": "static", "stream_url": "https://viamotionhsi.netplus.ch/live/eds/france24fr/browser-HLS8/france24fr.m3u8"},
    {"id": "eu-dw-en", "name": "DW English", "country": "EU", "group": "Internacional", "resolver": "static", "stream_url": "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8"},
]

COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Bélgica", "BG": "Bulgaria", "CH": "Suiza", "CY": "Chipre",
    "CZ": "Chequia", "DE": "Alemania", "DK": "Dinamarca", "EE": "Estonia", "ES": "España",
    "EU": "Europa", "FI": "Finlandia", "FR": "Francia", "GB": "Reino Unido", "GR": "Grecia",
    "HR": "Croacia", "HU": "Hungría", "IE": "Irlanda", "IS": "Islandia", "IT": "Italia",
    "LT": "Lituania", "LU": "Luxemburgo", "LV": "Letonia", "MT": "Malta", "NL": "Países Bajos",
    "NO": "Noruega", "PL": "Polonia", "PT": "Portugal", "RO": "Rumanía", "SE": "Suecia",
    "SI": "Eslovenia", "SK": "Eslovaquia",
}


def slugify_id(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def enrich(ch: dict) -> dict:
    out = dict(ch)
    code = out.get("country", "XX").upper()
    out["country"] = code
    out["country_name"] = COUNTRY_NAMES.get(code, code)
    out.setdefault("resolver", "static")
    out.setdefault("group", "Generalista")
    out.setdefault("enabled", True)
    if not out.get("logo"):
        out["logo"] = f"{LOGO}/{code.lower()}/default.png"
    return out


def write_channels(write: bool) -> int:
    by_country: dict[str, list[dict]] = {}
    seen: set[str] = set()
    skipped = 0
    for raw in CHANNELS:
        ch = enrich(raw)
        if ch.get("enabled") is False:
            skipped += 1
            continue
        cid = ch["id"]
        if cid in seen:
            skipped += 1
            continue
        seen.add(cid)
        code = ch["country"].lower()
        by_country.setdefault(code, []).append(ch)

    total = sum(len(v) for v in by_country.values())
    print(f"Países: {len(by_country)} | Canales: {total} | Omitidos: {skipped}")

    if not write:
        for code, items in sorted(by_country.items()):
            print(f"  {code}: {len(items)}")
        return total

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUT_DIR.glob("*.yaml"):
        path.unlink()

    for code, items in sorted(by_country.items()):
        path = OUT_DIR / f"{code}.yaml"
        payload = {"channels": items}
        path.write_text(
            yaml.dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        print(f"Wrote {path.name} ({len(items)} channels)")

    legacy = ROOT / "catalog" / "data" / "live-channels.yaml"
    legacy.write_text(
        "# Canales legacy migrados a catalog/data/live-channels/*.yaml\nchannels: []\n",
        encoding="utf-8",
    )
    print(f"Cleared legacy {legacy.name}")
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Escribir archivos YAML")
    args = parser.parse_args()
    total = write_channels(write=args.write)
    if total < 100:
        print(f"WARN: solo {total} canales (objetivo ~150)", file=sys.stderr)


if __name__ == "__main__":
    main()
