import os
import shutil
from datetime import date
from textwrap import dedent

import markdown2
import streamlit as st
from weasyprint import HTML

from crewai import Crew, Process
from trip_components import TripAgents, TripTasks
from trip_utils import capture_output

# ----------------------------
# Config & paths
# ----------------------------
OUTPUT_DIR = os.path.join(os.getcwd(), "viagem")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILES_MAP = {
    "roteiro_viagem.md": "roteiro_viagem.pdf",
    "guia_comunicacao.md": "guia_comunicacao.pdf",
    "relatorio_local.md": "relatorio_local.pdf",
    "relatorio_logistica.md": "relatorio_logistica.pdf",
}

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Planejamento de Viagens", page_icon="🌍", layout="centered")
st.title("🌍 Planejamento de Viagens (Multiagente)")

st.caption(
    "Preencha os campos e gere um roteiro completo com logística, guia de comunicação e relatórios auxiliares."
)

with st.form("trip_form"):
    st.subheader("Detalhes da viagem")
    col_a, col_b = st.columns(2)
    with col_a:
        from_city = st.text_input("Cidade de origem", value="")
    with col_b:
        destination_city = st.text_input("Cidade de destino", value="")

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("Data de partida", value=date.today())
    with col2:
        date_to = st.date_input("Data de retorno", value=date.today())

    interests = st.text_area(
        "Interesses e preferências",
        placeholder="Ex.: viagem romântica, museus, gastronomia local, tecnologia, arquitetura…",
    )

    submitted = st.form_submit_button("Gerar roteiro")

def load_markdown(file_path: str):
    """Carrega um arquivo .md e remove cercas ``` para exibir corretamente."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return content.replace("```markdown", "").replace("```", "")
    except Exception as e:
        st.error(f"Erro ao carregar {os.path.basename(file_path)}: {e}")
        return None

def convert_md_to_pdf(file_md: str, file_pdf: str):
    """Converte Markdown em PDF usando WeasyPrint."""
    text_md = load_markdown(file_md)
    if text_md:
        html_body = markdown2.markdown(text_md)
        style_css = """
        <style>
            body { font-family: Arial, Helvetica, sans-serif; font-size: 12pt; line-height: 1.5; }
            h1, h2, h3 { margin-top: 0.6em; }
            ul, ol { margin-left: 1.2em; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 8px; }
        </style>
        """
        full_html = f"<html><head>{style_css}</head><body>{html_body}</body></html>"
        HTML(string=full_html).write_pdf(file_pdf)

class TripCrew:
    """Orquestra a crew e executa as tasks em sequência."""
    def __init__(self, from_city, destination_city, date_from_str, date_to_str, interests):
        self.from_city = from_city
        self.destination_city = destination_city
        self.date_from = date_from_str
        self.date_to = date_to_str
        self.interests = interests

    def run(self):
        agents = TripAgents()
        tasks = TripTasks()

        city_info_agent = agents.city_info_agent()
        logistics_expert_agent = agents.logistics_expert_agent()
        itinerary_planner_agent = agents.itinerary_planner_agent()
        language_guide_agent = agents.language_guide_agent()

        city_info = tasks.city_info_task(
            city_info_agent,
            self.from_city,
            self.destination_city,
            self.interests,
            self.date_from,
            self.date_to
        )

        plan_logistics = tasks.plan_logistics_task(
            [city_info],
            logistics_expert_agent,
            self.destination_city,
            self.interests,
            self.date_from,
            self.date_to
        )

        build_itinerary = tasks.build_itinerary_task(
            [city_info, plan_logistics],
            itinerary_planner_agent,
            self.destination_city,
            self.interests,
            self.date_from,
            self.date_to
        )

        language_guide = tasks.language_guide_task(
            [build_itinerary],
            language_guide_agent,
            self.destination_city
        )

        crew = Crew(
            agents=[
                city_info_agent,
                logistics_expert_agent,
                itinerary_planner_agent,
                language_guide_agent
            ],
            tasks=[city_info, plan_logistics, build_itinerary, language_guide],
            process=Process.sequential,
            full_output=True,
            max_rpm=15,
            verbose=True
        )

        return crew.kickoff()

# ----------------------------
# Execução
# ----------------------------
if submitted:
    # validação simples
    if not (from_city and destination_city and interests):
        st.warning("Por favor, preencha todos os campos do formulário.")
        st.stop()

    if date_to < date_from:
        st.error("A data de retorno não pode ser anterior à data de partida.")
        st.stop()

    # Formata datas no padrão do roteiro
    date_from_str = date_from.strftime("%d de %B de %Y")
    date_to_str = date_to.strftime("%d de %B de %Y")

    # Status visual
    with st.status("Gerando seu roteiro (multiagente)...", expanded=True) as status:
        try:
            process_container = st.container(border=True)
            output_container = process_container.container(height=320)

            with capture_output(output_container):
                trip_crew = TripCrew(from_city, destination_city, date_from_str, date_to_str, interests)
                _ = trip_crew.run()

            status.update(label="✅ Roteiro gerado com sucesso!", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ Ocorreu um erro", state="error", expanded=True)
            st.exception(e)
            st.stop()

    # Converte MDs para PDF e move tudo para /viagem
    for md_file, pdf_name in FILES_MAP.items():
        if os.path.exists(md_file):
            convert_md_to_pdf(md_file, os.path.join(OUTPUT_DIR, pdf_name))

    for md_file in FILES_MAP.keys():
        if os.path.exists(md_file):
            shutil.move(md_file, os.path.join(OUTPUT_DIR, md_file))

    st.toast("Relatórios atualizados em ./viagem", icon="✅")

# Exibição dos relatórios (da execução atual ou anterior)
existing_mds = [md for md in FILES_MAP if os.path.exists(os.path.join(OUTPUT_DIR, md))]
if len(existing_mds) > 0:
    if not submitted:
        st.info("Exibindo relatórios da geração anterior.")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🗺️ Roteiro de Viagem", "📖 Guia de Comunicação", "📍 Relatório Cidade", "✈️ Relatório Logística"]
    )
    with tab1:
        md = load_markdown(os.path.join(OUTPUT_DIR, "roteiro_viagem.md"))
        if md: st.markdown(md)
    with tab2:
        md = load_markdown(os.path.join(OUTPUT_DIR, "guia_comunicacao.md"))
        if md: st.markdown(md)
    with tab3:
        md = load_markdown(os.path.join(OUTPUT_DIR, "relatorio_local.md"))
        if md: st.markdown(md)
    with tab4:
        md = load_markdown(os.path.join(OUTPUT_DIR, "relatorio_logistica.md"))
        if md: st.markdown(md)
