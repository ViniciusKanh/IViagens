# backend/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class PlanoRequisicao(BaseModel):
    cidade_origem: str
    destino: str
    data_inicio: str  # yyyy-mm-dd
    data_fim: str     # yyyy-mm-dd
    temas: List[str]
    numero_viajantes: int
    perfil: str
    teto_orcamento: float = 0.0
    moeda: str = "BRL"

class Leg(BaseModel):
    origem: str
    destino: str
    meio: str
    custo: float

class CustoItem(BaseModel):
    categoria: str
    valor: float

class DiaRoteiro(BaseModel):
    data: str
    custo_estimado_dia: float
    manha: Optional[str] = ""
    tarde: Optional[str] = ""
    noite: Optional[str] = ""
    narrativa: Optional[str] = ""

class PlanoResposta(BaseModel):
    destino: str
    data_inicio: str
    data_fim: str
    orcamento_estimado_total: float
    moedas: str
    legs: List[Leg]
    custos_itens: List[CustoItem]
    roteiro: List[DiaRoteiro]
    plano_html: str
    dentro_do_teto: bool
    sobra_ou_deficit: float
