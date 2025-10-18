
from __future__ import annotations

import os
import math
import random
from functools import lru_cache
from datetime import date, datetime, timedelta
from typing import List, Optional, Literal, Dict, Any, Tuple

import httpx
from dateutil.parser import isoparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ==========================
# Gemini (google-generativeai)
# ==========================
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

_genai_model = None
def _init_gemini():
    global _genai_model
    if _genai_model is not None:
        return _genai_model
    try:
        import google.generativeai as genai
        if not GEMINI_API_KEY:
            return None
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception as e:
        print(f"[warn] Gemini init falhou: {e}")
        _genai_model = None
    return _genai_model

def generate_text_with_llm(prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
    """
    Gera texto com Gemini. Se der erro ou não tiver API key, retorna string vazia.
    """
    try:
        model = _init_gemini()
        if model is None:
            return ""
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        if hasattr(resp, "text") and resp.text:
            return resp.text.strip()
        parts = []
        try:
            for c in resp.candidates or []:
                for p in getattr(c, "content", {}).parts or []:
                    if getattr(p, "text", ""):
                        parts.append(p.text)
            return "\n".join(parts).strip()
        except Exception:
            return ""
    except Exception as e:
        print(f"[warn] Erro Gemini: {e}")
        return ""

# ==========================
# Geocodificação (Nominatim/OSM) com cache e fallback
# ==========================
USE_ONLINE_GEOCODING = os.getenv("USE_ONLINE_GEOCODING", "1") != "0"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

@lru_cache(maxsize=256)
def geocode_city(query: str) -> tuple[float, float, str] | None:
    if not USE_ONLINE_GEOCODING:
        return None
    q = (query or "").strip()
    if not q:
        return None
    headers = {
        "User-Agent": "IViagem/2.3.0 (contato: suporte@ivg.local)",
        "Accept-Language": "pt-BR",
    }
    params = {"q": q, "format": "jsonv2", "limit": 1, "addressdetails": 0}
    try:
        with httpx.Client(timeout=5.0, headers=headers) as client:
            r = client.get(NOMINATIM_URL, params=params)
            if r.status_code != 200:
                return None
            data = r.json()
            if not data:
                return None
            item = data[0]
            lat = float(item["lat"])
            lon = float(item["lon"])
            label = item.get("display_name", q)
            return (lat, lon, label)
    except Exception:
        return None

# ==========================
# Geografia / cidades (catálogo local + aliases)
# ==========================
CITY_COORDS: Dict[str, tuple[float, float, str]] = {
    "são paulo": (-23.5505, -46.6333, "São Paulo, SP"),
    "rio de janeiro": (-22.9068, -43.1729, "Rio de Janeiro, RJ"),
    "manaus": (-3.1190, -60.0217, "Manaus, AM"),
    "belém": (-1.4558, -48.4902, "Belém, PA"),
    "brasília": (-15.7939, -47.8828, "Brasília, DF"),
    "salvador": (-12.9777, -38.5016, "Salvador, BA"),
    "recife": (-8.0476, -34.8770, "Recife, PE"),
    "curitiba": (-25.4284, -49.2733, "Curitiba, PR"),
    "porto alegre": (-30.0346, -51.2177, "Porto Alegre, RS"),
    "florianópolis": (-27.5949, -48.5482, "Florianópolis, SC"),
}

CITY_ALIASES = {
    "amazonia": "manaus",
    "amazônia": "manaus",
    "belem": "belém",
    "rio": "rio de janeiro",
    "sp": "são paulo",
}

def norm(s: str) -> str:
    return (s or "").strip().lower()

def resolve_city_key(raw: str) -> str:
    k = norm(raw)
    if k in CITY_COORDS:
        return k
    return CITY_ALIASES.get(k, k)

def get_coords_and_label(raw: str) -> tuple[float, float, str]:
    gc = geocode_city(raw)
    if gc is not None:
        return gc
    key = resolve_city_key(raw)
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    lat, lon, _ = CITY_COORDS["são paulo"]
    label = raw.strip() if raw.strip() else "Destino"
    return (lat, lon, label)

def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    (lat1, lon1), (lat2, lon2) = a, b
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(x), math.sqrt(1-x))

def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

# ==========================
# Modelos
# ==========================
PerfilType = Literal["econômico", "equilibrado", "premium"]

class PlanRequest(BaseModel):
    cidade_origem: str
    destino: str
    data_inicio: str
    data_fim: str
    temas: List[str] = Field(default_factory=list)
    numero_viajantes: int = Field(ge=1, default=1)
    perfil: PerfilType = Field(default="equilibrado")
    teto_orcamento: float = Field(ge=0, default=0.0)
    moeda: str = Field(default="BRL")

    @field_validator("data_inicio", "data_fim")
    @classmethod
    def _valida_data(cls, v: str) -> str:
        _ = isoparse(v).date()
        return v

class Leg(BaseModel):
    modo: Literal["voo", "rodoviário", "fluvial", "misto"]
    origem: str
    destino: str
    distancia_km: float
    duracao_h: float
    preco_estimado: float

class ItemCusto(BaseModel):
    categoria: str
    descricao: str
    quantidade: int
    preco_unitario: float
    custo_total: float

class DiaRoteiro(BaseModel):
    data: str
    manha: str
    tarde: str
    noite: str
    custo_estimado_dia: float
    narrativa: Optional[str] = ""

class PlanResponse(BaseModel):
    orcamento_estimado_total: float
    legs: List[Leg]
    custos_itens: List[ItemCusto]
    roteiro: List[DiaRoteiro]
    observacoes_gerais: Optional[str] = ""
    tempo_voo_total: Optional[str] = None
    economia_vs_base: Optional[float] = None
    risco_climatico: Optional[str] = None
    ajustes_aplicados: Optional[List[str]] = None
    periodo_ajustado: Optional[Dict[str, str]] = None
    teto_orcamento_utilizado: Optional[float] = None
    sugestoes: Optional[List[str]] = None

# ==========================
# Parâmetros de custo
# ==========================
PROFILE_FACTORS = {"econômico": 0.8, "equilibrado": 1.0, "premium": 1.6}
BASES = {
    "refeicoes": 120.0,
    "atividades": 80.0,
    "hospedagem": {
        "econômico": 220.0, "equilibrado": 350.0, "premium": 800.0
    },
    "voo_preco_km": 0.35,
    "rod_preco_km": 0.15,
}

POIS_MANAUS = [
    {"nome":"Teatro Amazonas","bairro":"Centro","slot":"tarde","tags":{"cultura"},"custo":60.0,"indoor":True},
    {"nome":"Palácio Rio Negro","bairro":"Centro","slot":"manha","tags":{"cultura"},"custo":0.0,"indoor":True},
    {"nome":"Museu da Cidade","bairro":"Centro","slot":"manha","tags":{"cultura"},"custo":20.0,"indoor":True},
    {"nome":"Mercado Adolpho Lisboa","bairro":"Centro","slot":"manha","tags":{"gastronomia","cultura"},"custo":0.0,"indoor":False},
    {"nome":"Café Regional no Centro","bairro":"Centro","slot":"manha","tags":{"gastronomia"},"custo":35.0,"indoor":True},
    {"nome":"Encontro das Águas (barco)","bairro":"Marina","slot":"manha","tags":{"natureza"},"custo":220.0,"indoor":False},
    {"nome":"MUSA – Museu da Amazônia","bairro":"Zona Norte","slot":"tarde","tags":{"natureza","cultura"},"custo":50.0,"indoor":False},
    {"nome":"Praia da Ponta Negra (pôr do sol)","bairro":"Ponta Negra","slot":"tarde","tags":{"natureza"},"custo":0.0,"indoor":False},
    {"nome":"Anavilhanas (day-trip)","bairro":"Marina","slot":"manha","tags":{"natureza"},"custo":480.0,"indoor":False},
    {"nome":"Praia da Lua","bairro":"Zona Oeste","slot":"tarde","tags":{"natureza"},"custo":0.0,"indoor":False},
    {"nome":"Jantar – Tacacá/Tambaqui","bairro":"Centro","slot":"noite","tags":{"gastronomia"},"custo":70.0,"indoor":True},
    {"nome":"Restaurante na Ponta Negra","bairro":"Ponta Negra","slot":"noite","tags":{"gastronomia"},"custo":95.0,"indoor":True},
    {"nome":"Bar com música regional","bairro":"Centro","slot":"noite","tags":{"cultura"},"custo":50.0,"indoor":True},
]

POIS_BELEM = [
    {"nome":"Ver-o-Peso","bairro":"Centro","slot":"manha","tags":{"gastronomia","cultura"},"custo":0.0,"indoor":False},
    {"nome":"Mangal das Garças","bairro":"Cidade Velha","slot":"tarde","tags":{"natureza"},"custo":20.0,"indoor":False},
    {"nome":"Basílica de Nazaré","bairro":"Nazaré","slot":"manha","tags":{"cultura"},"custo":0.0,"indoor":True},
    {"nome":"Estação das Docas","bairro":"Campina","slot":"noite","tags":{"gastronomia","cultura"},"custo":90.0,"indoor":True},
    {"nome":"Ilha do Combu (day-trip)","bairro":"Ribeirinha","slot":"manha","tags":{"natureza"},"custo":250.0,"indoor":False},
]

POIS_RIO = [
    {"nome":"Cristo Redentor","bairro":"Cosme Velho","slot":"manha","tags":{"cultura","natureza"},"custo":89.0,"indoor":False},
    {"nome":"Pão de Açúcar","bairro":"Urca","slot":"tarde","tags":{"natureza"},"custo":140.0,"indoor":False},
    {"nome":"Museu do Amanhã","bairro":"Centro","slot":"tarde","tags":{"cultura","tecnologia"},"custo":30.0,"indoor":True},
    {"nome":"Praia de Copacabana","bairro":"Zona Sul","slot":"manha","tags":{"natureza"},"custo":0.0,"indoor":False},
    {"nome":"Lapa à noite","bairro":"Lapa","slot":"noite","tags":{"cultura","gastronomia"},"custo":70.0,"indoor":True},
]

POIS_SAO_PAULO = [
    {"nome":"Avenida Paulista + MASP","bairro":"Paulista","slot":"tarde","tags":{"cultura"},"custo":50.0,"indoor":True},
    {"nome":"Beco do Batman","bairro":"Vila Madalena","slot":"manha","tags":{"cultura"},"custo":0.0,"indoor":False},
    {"nome":"Mercadão Municipal","bairro":"Centro","slot":"manha","tags":{"gastronomia"},"custo":40.0,"indoor":True},
    {"nome":"Ibirapuera","bairro":"Ibirapuera","slot":"tarde","tags":{"natureza"},"custo":0.0,"indoor":False},
    {"nome":"Rooftop/Bar (noite)","bairro":"Centro/Zona Sul","slot":"noite","tags":{"gastronomia"},"custo":80.0,"indoor":True},
]

POIS_GENERIC = [
    {"nome":"Centro histórico / praça principal","bairro":"Centro","slot":"manha","tags":{"cultura"},"custo":0.0,"indoor":False},
    {"nome":"Museu/galeria mais bem avaliado","bairro":"Centro","slot":"tarde","tags":{"cultura"},"custo":30.0,"indoor":True},
    {"nome":"Parque urbano / mirante","bairro":"Região central","slot":"tarde","tags":{"natureza"},"custo":0.0,"indoor":False},
    {"nome":"Mercado público / feira gastronômica","bairro":"Centro","slot":"manha","tags":{"gastronomia"},"custo":35.0,"indoor":True},
    {"nome":"Restaurante típico (noite)","bairro":"Centro","slot":"noite","tags":{"gastronomia"},"custo":80.0,"indoor":True},
]

CITY_POIS = {
    "manaus": POIS_MANAUS,
    "belém": POIS_BELEM,
    "rio de janeiro": POIS_RIO,
    "são paulo": POIS_SAO_PAULO,
}

def get_pois_for_city(raw_city: str) -> List[Dict[str, Any]]:
    key = resolve_city_key(raw_city)
    if key in CITY_POIS:
        return CITY_POIS[key]
    alias = CITY_ALIASES.get(key)
    if alias and alias in CITY_POIS:
        return CITY_POIS[alias]
    return POIS_GENERIC

def filter_pois(pois: List[Dict[str, Any]], tags: List[str], slot: str, indoor: Optional[bool] = None) -> List[Dict[str, Any]]:
    filtered = []
    for poi in pois:
        if slot != "" and poi["slot"] != slot:
            continue
        if indoor is not None and poi["indoor"] != indoor:
            continue
        if tags and not any(t in poi["tags"] for t in tags):
            continue
        filtered.append(poi)
    return filtered

def get_random_poi(pois: List[Dict[str, Any]], exclude: List[str] = []) -> Optional[Dict[str, Any]]:
    available = [p for p in pois if p["nome"] not in exclude]
    if not available:
        return None
    return random.choice(available)

# ==========================
# Lógica de planejamento principal
# ==========================
def recompute_plan(req: 'PlanRequest', d0: date, d1: date, perfil: PerfilType,
                   force_transport: Optional[str] = None, meals_factor: float = 1.0,
                   cap_paid: Optional[float] = None, budget_mode: bool = False,
                   allow_daytrips: bool = True):
    total_orcamento = 0.0
    legs: List[Leg] = []
    custos_itens: List[ItemCusto] = []
    roteiro: List[DiaRoteiro] = []

    lat_o, lon_o, origem_label = get_coords_and_label(req.cidade_origem)
    lat_d, lon_d, destino_label = get_coords_and_label(req.destino)
    origem_coords = (lat_o, lon_o)
    destino_coords = (lat_d, lon_d)
    distancia_total_km = haversine_km(origem_coords, destino_coords)

    modo_ida = force_transport if force_transport else ("voo" if distancia_total_km > 500 else "rodoviário")
    preco_ida = distancia_total_km * BASES["voo_preco_km"] if modo_ida == "voo" else distancia_total_km * BASES["rod_preco_km"]
    duracao_ida = distancia_total_km / 700 if modo_ida == "voo" else distancia_total_km / 80
    legs.append(Leg(modo=modo_ida, origem=origem_label, destino=destino_label, distancia_km=distancia_total_km, duracao_h=duracao_ida, preco_estimado=preco_ida * req.numero_viajantes))
    total_orcamento += preco_ida * req.numero_viajantes
    custos_itens.append(ItemCusto(categoria="Transporte", descricao=f"{modo_ida} - Ida", quantidade=req.numero_viajantes, preco_unitario=preco_ida, custo_total=preco_ida * req.numero_viajantes))

    if d0 != d1:
        modo_volta = force_transport if force_transport else ("voo" if distancia_total_km > 500 else "rodoviário")
        preco_volta = distancia_total_km * BASES["voo_preco_km"] if modo_volta == "voo" else distancia_total_km * BASES["rod_preco_km"]
        duracao_volta = distancia_total_km / 700 if modo_volta == "voo" else distancia_total_km / 80
        legs.append(Leg(modo=modo_volta, origem=destino_label, destino=origem_label, distancia_km=distancia_total_km, duracao_h=duracao_volta, preco_estimado=preco_volta * req.numero_viajantes))
        total_orcamento += preco_volta * req.numero_viajantes
        custos_itens.append(ItemCusto(categoria="Transporte", descricao=f"{modo_volta} - Volta", quantidade=req.numero_viajantes, preco_unitario=preco_volta, custo_total=preco_volta * req.numero_viajantes))

    num_dias = (d1 - d0).days + 1
    fator_perfil = PROFILE_FACTORS[perfil]
    pois_destino = get_pois_for_city(req.destino)

    for current_date in daterange(d0, d1):
        custo_dia = 0.0
        dia_str = current_date.isoformat()
        atividades_manha: List[str] = []
        atividades_tarde: List[str] = []
        atividades_noite: List[str] = []

        if num_dias > 1:
            preco_hospedagem_noite = BASES["hospedagem"][perfil]
            custo_hospedagem_dia = preco_hospedagem_noite * req.numero_viajantes / num_dias
            custo_dia += custo_hospedagem_dia
            custos_itens.append(ItemCusto(categoria="Hospedagem", descricao=f"Diária ({perfil})", quantidade=req.numero_viajantes, preco_unitario=preco_hospedagem_noite / num_dias, custo_total=custo_hospedagem_dia))

        custo_refeicoes_dia = BASES["refeicoes"] * req.numero_viajantes * fator_perfil * meals_factor
        custo_dia += custo_refeicoes_dia
        custos_itens.append(ItemCusto(categoria="Alimentação", descricao=f"Refeições ({perfil})", quantidade=req.numero_viajantes, preco_unitario=BASES["refeicoes"] * fator_perfil * meals_factor, custo_total=custo_refeicoes_dia))

        poi_manha = get_random_poi(filter_pois(pois_destino, req.temas, "manha", indoor=False if not is_weekend(current_date) else None))
        if poi_manha and (not budget_mode or (cap_paid is not None and poi_manha["custo"] <= cap_paid)):
            atividades_manha.append(poi_manha["nome"])
            custo_dia += poi_manha["custo"] * req.numero_viajantes
            custos_itens.append(ItemCusto(categoria="Atividade", descricao=poi_manha["nome"], quantidade=req.numero_viajantes, preco_unitario=poi_manha["custo"], custo_total=poi_manha["custo"] * req.numero_viajantes))

        poi_tarde = get_random_poi(filter_pois(pois_destino, req.temas, "tarde"), exclude=[p["nome"] for p in [poi_manha] if p])
        if poi_tarde and (not budget_mode or (cap_paid is not None and poi_tarde["custo"] <= cap_paid)):
            atividades_tarde.append(poi_tarde["nome"])
            custo_dia += poi_tarde["custo"] * req.numero_viajantes
            custos_itens.append(ItemCusto(categoria="Atividade", descricao=poi_tarde["nome"], quantidade=req.numero_viajantes, preco_unitario=poi_tarde["custo"], custo_total=poi_tarde["custo"] * req.numero_viajantes))

        poi_noite = get_random_poi(filter_pois(pois_destino, req.temas, "noite"), exclude=[p["nome"] for p in [poi_manha, poi_tarde] if p])
        if poi_noite and (not budget_mode or (cap_paid is not None and poi_noite["custo"] <= cap_paid)):
            atividades_noite.append(poi_noite["nome"])
            custo_dia += poi_noite["custo"] * req.numero_viajantes
            custos_itens.append(ItemCusto(categoria="Atividade", descricao=poi_noite["nome"], quantidade=req.numero_viajantes, preco_unitario=poi_noite["custo"], custo_total=poi_noite["custo"] * req.numero_viajantes))

        roteiro.append(DiaRoteiro(
            data=dia_str,
            manha=", ".join(atividades_manha) or "Atividade livre",
            tarde=", ".join(atividades_tarde) or "Atividade livre",
            noite=", ".join(atividades_noite) or "Atividade livre",
            custo_estimado_dia=custo_dia
        ))
        total_orcamento += custo_dia

    return total_orcamento, legs, custos_itens, roteiro

def fit_to_budget(req: PlanRequest, d0: date, d1: date):
    ajustes: List[str] = []
    periodo_ajustado: Optional[Dict[str, str]] = None
    sugestoes: Optional[List[str]] = None

    perfil = req.perfil
    force_transport: Optional[str] = None
    meals_factor = 1.0
    cap_paid: Optional[float] = None
    budget_mode = False
    allow_daytrips = True

    total, legs, custos, roteiro = recompute_plan(req, d0, d1, perfil)
    if req.teto_orcamento <= 0 or total <= req.teto_orcamento:
        return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

    if any(l.modo == "voo" for l in legs):
        force_transport = "rodoviário"
        total2, legs2, custos2, roteiro2 = recompute_plan(req, d0, d1, perfil, force_transport=force_transport)
        if total2 < total:
            total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
            ajustes.append("Transporte ajustado para rodoviário (mais econômico).")
    if total <= req.teto_orcamento:
        return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

    if perfil == "premium":
        perfil = "equilibrado"
        total2, legs2, custos2, roteiro2 = recompute_plan(req, d0, d1, perfil, force_transport)
        if total2 < total:
            total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
            ajustes.append("Hospedagem ajustada para perfil 'equilibrado'.")
    if total > req.teto_orcamento and perfil in ("equilibrado", "premium"):
        perfil = "econômico"
        total2, legs2, custos2, roteiro2 = recompute_plan(req, d0, d1, perfil, force_transport)
        if total2 < total:
            total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
            ajustes.append("Hospedagem ajustada para perfil 'econômico'.")
    if total <= req.teto_orcamento:
        return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

    budget_mode = True
    cap_paid = 60.0
    total2, legs2, custos2, roteiro2 = recompute_plan(req, d0, d1, perfil, force_transport, cap_paid=cap_paid, budget_mode=budget_mode)
    if total2 < total:
        total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
        ajustes.append("Atividades priorizadas para opções gratuitas/baixas (teto por pessoa/dia).")
    if total <= req.teto_orcamento:
        return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

    allow_daytrips = False
    total2, legs2, custos2, roteiro2 = recompute_plan(req, d0, d1, perfil, force_transport, cap_paid=cap_paid, budget_mode=budget_mode, allow_daytrips=allow_daytrips)
    if total2 < total:
        total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
        ajustes.append("Day-trips removidas.")
    if total <= req.teto_orcamento:
        return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

    meals_factor = 0.85
    total2, legs2, custos2, roteiro2 = recompute_plan(req, d0, d1, perfil, force_transport, meals_factor=meals_factor, cap_paid=cap_paid, budget_mode=budget_mode, allow_daytrips=allow_daytrips)
    if total2 < total:
        total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
        ajustes.append("Alimentação otimizada (~15% mais em conta).")
    if total <= req.teto_orcamento:
        return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

    cur_d1 = d1
    while total > req.teto_orcamento and (cur_d1 - d0).days + 1 > 2:
        cur_d1 = cur_d1 - timedelta(days=1)
        total2, legs2, custos2, roteiro2 = recompute_plan(
            req, d0, cur_d1, perfil, force_transport, meals_factor, cap_paid, budget_mode, allow_daytrips
        )
        if total2 < total:
            total, legs, custos, roteiro = total2, legs2, custos2, roteiro2
            periodo_ajustado = {"data_inicio": d0.isoformat(), "data_fim": cur_d1.isoformat()}
            ajustes.append("Viagem encurtada ao final para adequar ao orçamento.")

    if total > req.teto_orcamento:
        sugestoes = [
            "Considere reduzir o número de viajantes ou dividir quartos.",
            "Aumente o teto de orçamento ou viaje em baixa temporada.",
            "Escolha somente atrações gratuitas durante alguns dias.",
        ]

    return total, {"legs": legs, "custos": custos, "roteiro": roteiro}, ajustes, periodo_ajustado, sugestoes

def risk_tag(raw_dest: str) -> str:
    k = resolve_city_key(raw_dest)
    if k in ("manaus", "belém"):
        return "Médio (chuvas tropicais / calor úmido)"
    return "Baixo"

APP_VERSION = "2.3.0"
app = FastAPI(title="IViagem Backend (Smart + Budget + Geocode + Gemini)", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}

@app.get("/info")
def info():
    return {"name": "IViagem Planner (smart + budget + geocode + gemini)",
            "version": APP_VERSION, "endpoints": ["/health", "/info", "/plan"]}

@app.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    try:
        d0 = isoparse(req.data_inicio).date()
        d1 = isoparse(req.data_fim).date()
    except Exception:
        raise HTTPException(status_code=400, detail="Datas inválidas (use YYYY-MM-DD).")
    if d1 < d0:
        raise HTTPException(status_code=400, detail="data_fim não pode ser anterior a data_inicio.")

    total, parts, ajustes, periodo_ajustado, sugestoes = fit_to_budget(req, d0, d1)

    legs = parts["legs"]
    custos_itens = parts["custos"]
    roteiro = parts["roteiro"]

    tempo_voo_total = None
    if any(l.modo == "voo" for l in legs):
        tempo_voo_total = f"{round(sum(l.duracao_h for l in legs), 1)} h"

    economia_vs_base = None
    if req.teto_orcamento and req.teto_orcamento > 0:
        economia_vs_base = round(req.teto_orcamento - total, 2)

    _, _, destino_label = get_coords_and_label(req.destino)
    risco = risk_tag(req.destino)

    periodo_txt = ""
    if periodo_ajustado and (periodo_ajustado['data_inicio'] != req.data_inicio or periodo_ajustado['data_fim'] != req.data_fim):
        periodo_txt = f" Período ajustado: {periodo_ajustado['data_inicio']} a {periodo_ajustado['data_fim']}."

    temas_txt = ", ".join(req.temas)
    obs_prompt = (
        "Você é um assistente de viagens. "
        f"Gere uma observação geral para um planejamento de viagem de {req.cidade_origem} para {destino_label}, "
        f"de {req.data_inicio} a {req.data_fim}, para {req.numero_viajantes} viajantes, com perfil {req.perfil}. "
        f"Interesses: {temas_txt}. O orçamento total estimado é de {total:.2f} {req.moeda}.{periodo_txt} "
        f"Inclua informações sobre o risco climático ( {risco} ). Seja inspirador, prático e personalizado."
    )
    obs = generate_text_with_llm(obs_prompt, max_tokens=220, temperature=0.8)
    if not obs:
        obs = (
            f"Planejamento inteligente com adaptação automática ao orçamento."
            f" Período solicitado: {req.data_inicio} a {req.data_fim}.{periodo_txt} Moeda: {req.moeda}."
        )

    for dia in roteiro:
        dia_prompt = (
            f"Crie uma narrativa curta para o dia {dia.data} em {destino_label}. "
            f"Atividades: manhã - {dia.manha}; tarde - {dia.tarde}; noite - {dia.noite}. "
            f"Custo estimado do dia: {dia.custo_estimado_dia:.2f} {req.moeda}. "
            f"Risco climático geral: {risco}. Foque em {temas_txt}."
        )
        narrativa = generate_text_with_llm(dia_prompt, max_tokens=150, temperature=0.9)
        dia.narrativa = narrativa or ""

    if sugestoes is None:
        sugestao_prompt = (
            f"Com base no planejamento {req.cidade_origem} → {destino_label} ({req.data_inicio} a {req.data_fim}), "
            f"{req.numero_viajantes} viajantes, perfil {req.perfil}, interesses em {temas_txt} e orçamento de {total:.2f} {req.moeda}, "
            "gere 3 sugestões curtas e práticas para melhorar a experiência ou economizar."
        )
        llm_sugestoes_str = generate_text_with_llm(sugestao_prompt, max_tokens=300, temperature=0.9)
        if llm_sugestoes_str:
            sugestoes = [s.strip("-• ").strip() for s in llm_sugestoes_str.splitlines() if s.strip()]
        else:
            sugestoes = [
                "Use transporte público local para deslocamentos curtos.",
                "Busque menus executivos no almoço para economizar.",
                "Inclua atividades gratuitas em dias alternados.",
            ]

    return PlanResponse(
        orcamento_estimado_total=total,
        legs=legs,
        custos_itens=custos_itens,
        roteiro=roteiro,
        observacoes_gerais=obs,
        tempo_voo_total=tempo_voo_total,
        economia_vs_base=economia_vs_base,
        risco_climatico=risco,
        ajustes_aplicados=ajustes or None,
        periodo_ajustado=periodo_ajustado if periodo_txt else None,
        teto_orcamento_utilizado=req.teto_orcamento if req.teto_orcamento > 0 else None,
        sugestoes=sugestoes or None,
    )

@app.get("/geocode")
def geocode(q: str):
    gc = geocode_city(q)
    if gc is None:
        lat, lon, label = get_coords_and_label(q)
        return {"online": None, "fallback": {"lat": lat, "lon": lon, "label": label}}
    lat, lon, label = gc
    return {"online": {"lat": lat, "lon": lon, "label": label}}
