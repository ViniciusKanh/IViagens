from crewai.tools import tool
from langchain_tavily import TavilySearch
from langchain_community.tools import DuckDuckGoSearchResults

def _safe_tavily(query: str, max_results=4):
    try:
        search_tavily = TavilySearch(max_results=max_results)
        return search_tavily.invoke(query)
    except Exception as e:
        return {"error": f"Tavily indisponível: {e}"}

class SearchTools:
    @tool("Pesquisa na internet (com fallback)")
    def search_web(query: str = "") -> str:
        """
        Tenta Tavily primeiro; se indisponível, usa DuckDuckGo automaticamente.
        """
        r = _safe_tavily(query)
        if isinstance(r, dict) and r.get("error"):
            # Fallback
            try:
                ddg = DuckDuckGoSearchResults(num_results=4, verbose=True)
                return ddg.run(query)
            except Exception as e:
                return f"Falha geral de busca (rede?): {e}"
        return r

class CalculatorTools:
    @tool("Faça um cálculo")
    def calculate(operation):
        try:
            return eval(operation)
        except SyntaxError:
            return "Erro: Sintaxe inválida"
        except Exception as e:
            return f"Erro ao calcular: {e}"
