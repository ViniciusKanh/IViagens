# backend/orchestrator.py
from backend.schemas import PlanoRequisicao, PlanoResposta, Leg, CustoItem, DiaRoteiro

class Orchestrator:
    def __init__(self):
        pass

    async def run(self, req: PlanoRequisicao) -> PlanoResposta:
        # Simulação de lógica de planejamento
        legs = [
            Leg(origem=req.cidade_origem, destino=req.destino, meio="Avião", custo=900.0)
        ]
        custos_itens = [
            CustoItem(categoria="Transporte", valor=900.0),
            CustoItem(categoria="Hospedagem", valor=1200.0)
        ]
        roteiro = [
            DiaRoteiro(
                data=req.data_inicio,
                custo_estimado_dia=200.0,
                manha="Passeio cultural",
                tarde="Museu de História",
                noite="Jantar típico",
                narrativa="Dia focado em cultura local."
            )
        ]
        total = sum(item.valor for item in custos_itens)
        plano_html = f"<h2>Roteiro para {req.destino}</h2><p>Hospedagem, transporte e cultura!</p>"
        sobra = req.teto_orcamento - total if req.teto_orcamento > 0 else 0
        dentro_do_teto = sobra >= 0

        return PlanoResposta(
            destino=req.destino,
            data_inicio=req.data_inicio,
            data_fim=req.data_fim,
            orcamento_estimado_total=total,
            moedas=req.moeda,
            legs=legs,
            custos_itens=custos_itens,
            roteiro=roteiro,
            plano_html=plano_html,
            dentro_do_teto=dentro_do_teto,
            sobra_ou_deficit=sobra
        )
