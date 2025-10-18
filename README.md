# IViagem – Planejador de Viagens Inteligente

Um **planejador de viagens inteligente** que utiliza IA para gerar roteiros personalizados, otimizar orçamentos e fornecer narrativas envolventes para cada dia da sua viagem, com uma experiência de usuário moderna e intuitiva.

## 🌟 Características Principais

### Backend Inteligente
- **Geocodificação em tempo real** via Nominatim/OpenStreetMap
- **Adaptação automática ao orçamento** com múltiplas estratégias de otimização, respeitando as datas de viagem.
- **Integração com LLM (Gemini 2.5 Flash)** para narrativas diárias ricas, observações gerais detalhadas e sugestões personalizadas.
- **Cálculo inteligente de custos** por perfil (econômico, equilibrado, premium).
- **Sugestões contextualizadas** baseadas no tipo de viagem e orçamento.

### Frontend Ultra-Moderno e Dinâmico
- **Design futurista e responsivo** que se adapta perfeitamente a qualquer dispositivo (desktop, tablet, mobile).
- **Splash screen animada** com o logo profissional do IViagem, garantindo uma entrada de impacto.
- **Interface intuitiva e dinâmica** com animações suaves, transições elegantes e efeitos visuais modernos (como glassmorphism e shimmer).
- **Exibição dinâmica de resultados** com cards interativos e animações de entrada em cascata.
- **Itinerário dia a dia** detalhado com narrativas envolventes geradas por IA.
- **Funcionalidade de Exportação para PDF estilizada e bonita**, permitindo salvar o roteiro completo com um layout profissional e visualmente atraente para fácil compartilhamento e consulta offline.

## 📋 Requisitos

### Backend
- Python 3.8+
- FastAPI
- Pydantic
- httpx
- python-dateutil
- `openai` (para integração com LLM, usando o modelo Gemini)

### Frontend
- Navegador moderno (Chrome, Firefox, Safari, Edge)
- Sem dependências externas (HTML/CSS/JavaScript puro, com bibliotecas para PDF export)

## 🚀 Instalação e Execução

### 1. Clonar o Repositório
```bash
git clone <seu-repositorio>
cd IViagem
```

### 2. Configurar o Backend

#### Instalar Dependências
```bash
cd backend
pip install -r requirements.txt
```

#### Configurar Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto (na mesma pasta do `backend` e `frontend`) e adicione suas chaves de API:

```
GEMINI_API_KEY="sua-chave-api-gemini-aqui"
TAVILY_API_KEY="sua-chave-api-tavily-aqui" # Opcional, para futuras integrações de pesquisa
GROQ_API_KEY="sua-chave-api-groq-aqui"     # Opcional, para futuras integrações de LLM
```

**Nota:** Atualmente, o projeto utiliza a `GEMINI_API_KEY` via a interface `openai` para o modelo `gemini-2.5-flash`. As outras chaves (`TAVILY_API_KEY`, `GROQ_API_KEY`) são preparadas para futuras expansões e integrações de funcionalidades.

#### Executar o Backend
```bash
uvicorn app:app --reload --port 8000
```

O backend estará disponível em `http://127.0.0.1:8000`

### 3. Servir o Frontend

#### Opção 1: Usando Python (simples)
```bash
cd frontend
python -m http.server 8080
```

Acesse em `http://localhost:8080`

#### Opção 2: Usando Node.js (http-server)
```bash
cd frontend
npx http-server -p 8080
```

#### Opção 3: Usando Live Server (VS Code)
Instale a extensão "Live Server" e clique em "Go Live"

## 📖 Como Usar

1. **Abra o Frontend** em seu navegador.
2. **Preencha os campos** no formulário de planejamento:
   - Cidade de origem
   - Cidade de destino
   - Datas de partida e retorno
   - Número de viajantes
   - Perfil de viagem (econômico, equilibrado, premium)
   - Interesses e preferências (separados por vírgula)
   - Teto de orçamento (opcional)

3. **Clique em "Gerar Roteiro Inteligente"** para que a IA crie seu plano de viagem.
4. **Visualize os resultados** que aparecerão de forma dinâmica e interativa:
   - Resumo executivo com orçamento total, duração e risco climático.
   - Logística de transporte detalhada.
   - Orçamento detalhado por categoria.
   - Itinerário dia a dia com narrativas envolventes.
   - Sugestões personalizadas e ajustes aplicados (se houver).
5. **Exporte seu roteiro para PDF** clicando no botão "Baixar Roteiro em PDF" na seção de resultados para obter uma versão estilizada e imprimível.

## 🔧 Endpoints da API

### GET `/health`
Verifica o status da API.

**Resposta:**
```json
{
  "status": "ok",
  "ts": "2025-10-18T12:00:00.000000"
}
```

### GET `/info`
Retorna informações sobre a API.

**Resposta:**
```json
{
  "name": "IViagem Planner (smart + budget + geocode)",
  "version": "2.3.0",
  "endpoints": ["/health", "/info", "/plan", "/geocode"]
}
```

### POST `/plan`
Gera um plano de viagem personalizado.

**Payload:**
```json
{
  "cidade_origem": "São Paulo",
  "destino": "Manaus",
  "data_inicio": "2025-11-01",
  "data_fim": "2025-11-07",
  "numero_viajantes": 2,
  "perfil": "equilibrado",
  "temas": ["cultura", "gastronomia", "natureza"],
  "teto_orcamento": 5000.0,
  "moeda": "BRL"
}
```

**Resposta:**
```json
{
  "orcamento_estimado_total": 4850.50,
  "legs": [
    {
      "modo": "voo",
      "origem": "São Paulo, SP",
      "destino": "Manaus, AM",
      "distancia_km": 2500,
      "duracao_h": 3.5,
      "preco_estimado": 1400.0
    }
  ],
  "custos_itens": [...],
  "roteiro": [
    {
      "data": "2025-11-01",
      "manha": "Chegada em Manaus",
      "tarde": "Check-in e exploração da região",
      "noite": "Jantar em restaurante local",
      "custo_estimado_dia": 450.0,
      "narrativa": "Seu primeiro dia em Manaus promete ser mágico..."
    }
  ],
  "observacoes_gerais": "Planejamento inteligente realizado com sucesso...",
  "tempo_voo_total": "3.5 h",
  "economia_vs_base": 149.50,
  "risco_climatico": "Médio (chuvas tropicais / calor úmido)",
  "ajustes_aplicados": [],
  "sugestoes": [...]
}
```

### GET `/geocode?q=<cidade>`
Geocodifica uma cidade.

**Resposta:**
```json
{
  "online": {
    "lat": -3.1190,
    "lon": -60.0217,
    "label": "Manaus, Amazonas, Brasil"
  }
}
```

## 🎨 Paleta de Cores

| Cor | Hex | Uso |
|-----|-----|-----|
| Verde Primário | `#10b981` | Elementos principais, botões, destaques |
| Azul Primário | `#0ea5e9` | Acentos, gradientes, títulos |
| Preto Escuro | `#0a0e27` | Fundo principal, texto secundário |
| Branco | `#f8fafc` | Texto principal, ícones |
| Verde Acento | `#34d399` | Hover, destaque, bordas |
| Azul Acento | `#38bdf8` | Gradientes, sombras |
| Roxo Acento | `#a78bfa` | Gradientes, elementos futuristas |
| Rosa Acento | `#ec4899` | Gradientes, elementos futuristas |

## 📊 Estrutura de Dados

### Modelo de Resposta (PlanResponse)
```python
{
  "orcamento_estimado_total": float,
  "legs": List[Leg],
  "custos_itens": List[ItemCusto],
  "roteiro": List[DiaRoteiro],
  "observacoes_gerais": str,
  "tempo_voo_total": str,
  "economia_vs_base": float,
  "risco_climatico": str,
  "ajustes_aplicados": List[str],
  "periodo_ajustado": Dict[str, str],
  "teto_orcamento_utilizado": float,
  "sugestoes": List[str]
}
```

## 🔐 Segurança

- **CORS habilitado** para aceitar requisições de qualquer origem (configurável)
- **Validação de entrada** em todos os endpoints
- **Tratamento de erros** robusto
- **Chaves de API** protegidas em variáveis de ambiente (`.env`)

## 📝 Licença

Este projeto é fornecido como está, sem garantias. Sinta-se livre para usar, modificar e distribuir.

## 👨‍💻 Desenvolvimento

### Stack
- **Backend**: FastAPI, Python 3.8+
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Font Awesome, jsPDF, html2canvas
- **IA**: Google Gemini (via OpenAI API, modelo `gemini-2.5-flash`)
- **Geocodificação**: Nominatim/OpenStreetMap

### Estrutura do Projeto
```
IViagem/
├── backend/
│   ├── app.py              # Aplicação FastAPI principal
│   ├── requirements.txt    # Dependências Python
│   └── __init__.py
│
├── frontend/
│   ├── index.html          # Interface web ultra-moderna
│   └── assets/
│       ├── logo.png        # Logo do projeto
│       └── splash.png      # Splash screen (se aplicável)
│   ├── trip_components.py
│   ├── trip_utils.py
│   ├── trip_tools.py
│   └── __init__.py
│
├── .env                    # Variáveis de ambiente (GEMINI_API_KEY, TAVILY_API_KEY, GROQ_API_KEY)
├── IViagem_README.md       # Documentação completa do projeto
├── QUICK_START.md          # Guia de início rápido
└── requirements.txt        # Dependências gerais (se unificadas)
```

---

**IViagem** – Tornando o planejamento de viagens inteligente, fácil e divertido! ✈️🌍
