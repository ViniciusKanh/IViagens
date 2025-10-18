# backend/agents.py

class AgentDiscovery:
    def sugerir_activities(self, destino, temas, perfil, teto, ndias):
        # Simulação simples
        return [
            {"nome": "Passeio cultural", "custo": 100.0, "descricao": "Visita guiada no centro histórico"},
            {"nome": "Museu de História", "custo": 60.0, "descricao": "Entrada no museu local"}
        ], ["Atividades sugeridas baseadas em perfil/cultura."]

class AgentLogistics:
    def planejar(self, origem, destino, n_viajantes, moeda, budget_per_person):
        return [
            {"origem": origem, "destino": destino, "meio": "Avião", "custo": 900.0}
        ]

class AgentBudget:
    def estimar_livre(self, legs, perfil, ndias, nviaj):
        total = sum(leg['custo'] for leg in legs) + 1200.0
        custos_itens = [
            {"categoria": "Transporte", "valor": sum(leg['custo'] for leg in legs)},
            {"categoria": "Hospedagem", "valor": 1200.0}
        ]
        just = ["Orçamento baseado em simulação."]
        return total, custos_itens, just

class AgentItinerary:
    def montar(self, ndias, pois, perfil, passeios_total, data_inicio):
        roteiro = []
        from datetime import datetime, timedelta
        data_base = datetime.strptime(data_inicio, "%Y-%m-%d")
        for i in range(ndias):
            dia = data_base + timedelta(days=i)
            roteiro.append({
                "data": dia.strftime("%Y-%m-%d"),
                "custo_estimado_dia": 200.0,
                "manha": "Passeio cultural" if i == 0 else "",
                "tarde": "Museu de História" if i == 0 else "",
                "noite": "Jantar típico" if i == 0 else "",
                "narrativa": "Dia focado em cultura local." if i == 0 else ""
            })
        notes_rot = ["Roteiro planejado para maximizar experiências culturais."]
        return roteiro, notes_rot

class FinalWriter:
    def run(self, contexto, legs, custos_itens, roteiro, activities, notas):
        # Gera HTML final
        html = f"<h2>Roteiro para {contexto['destino']}</h2><ul>"
        for dia in roteiro:
            html += f"<li>{dia['data']}: {dia.get('manha','')} - {dia.get('tarde','')} - {dia.get('noite','')}</li>"
        html += "</ul>"
        return html
