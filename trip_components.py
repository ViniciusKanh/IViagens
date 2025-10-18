import os
from textwrap import dedent
from dotenv import load_dotenv
from crewai import Agent, Task, LLM
from trip_tools import SearchTools, CalculatorTools

load_dotenv()

def _make_llm():
    # Se a Google API não estiver acessível/rede bloquear, vamos capturar erro na hora da execução
    return LLM(
        model="gemini/gemini-2.0-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
        # timeout e retries ajudam a não travar
        temperature=0.3,
        max_tokens=2000,
        request_timeout=30,
        max_retries=1,
    )

class TripAgents:
    def __init__(self):
        self.gemini = _make_llm()

    def city_info_agent(self):
        return Agent(
            role="Especialista em informações da cidade",
            goal="Reunir informações úteis sobre o destino escolhido.",
            backstory="Especialista em clima, eventos e cultura local.",
            llm=self.gemini,
            tools=[SearchTools.search_web],
            verbose=True,
            max_iter=8,
            allow_delegation=False,
        )

    def logistics_expert_agent(self):
        return Agent(
            role="Especialista em logística de viagem",
            goal="Identificar melhores opções de transporte, hospedagem e deslocamento.",
            backstory="Foco em segurança, localização e custo-benefício.",
            llm=self.gemini,
            tools=[SearchTools.search_web, CalculatorTools.calculate],
            verbose=True,
            max_iter=8,
            allow_delegation=False,
        )

    def itinerary_planner_agent(self):
        return Agent(
            role="Planejador de itinerário",
            goal="Criar roteiro diário equilibrado com base nas preferências.",
            backstory="Integra clima, atrações e logística.",
            llm=self.gemini,
            tools=[SearchTools.search_web],
            verbose=True,
            max_iter=8,
            allow_delegation=False,
        )

    def language_guide_agent(self):
        return Agent(
            role="Guia de comunicação e etiqueta",
            goal="Frases úteis e dicas culturais por situação.",
            backstory="Facilita a comunicação no destino.",
            llm=self.gemini,
            tools=[SearchTools.search_web],
            verbose=True,
            max_iter=5,
            allow_delegation=False,
        )
