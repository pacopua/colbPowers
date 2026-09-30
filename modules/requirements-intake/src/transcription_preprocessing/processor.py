import datetime
from langchain_tavily import TavilySearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from loguru import logger
from typing import List, Dict, Any, Optional
from .config_models import build_llm
from .structure_models import IssueList, ResearchPlan

from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
class TranscriptionProcessor:
    def __init__(self):
        self.cheap_llm : AzureChatOpenAI|ChatGoogleGenerativeAI = build_llm(source="Azure")
        self.good_llm : AzureChatOpenAI|ChatGoogleGenerativeAI = build_llm(source="Google")
        # 4000 words approx 20000-25000 chars. Let's aim safely.
        # User requested 4000-6000 words.
        # Overlap 200 words (~1000-1200 chars).
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=25000, 
            chunk_overlap=1200,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=len
        )
        
        year_back = datetime.datetime.now() - datetime.timedelta(days=365)
        year_back_string = year_back.strftime("%Y-%m-%d")
        self.search_tool = TavilySearch(
            max_results=3,             # Solo 3 resultados para no saturar
            search_depth="advanced",   # Búsqueda profunda para temas técnicos
            include_answer=True,       # ¡Truco! Tavily resume la respuesta (ahorra trabajo al LLM)
            include_raw_content=False, # False para ahorrar tokens de entrada en tu LLM
            # include_images=False     # No necesitamos imágenes para código,
            start_date=year_back_string #Ejemplo: "2023-01-15" para resultados recientes
        )

    def generate_research_plan(self, transcript_text: str, max_queries: int = 3) -> Dict[str, Any]:
        """
        Analiza la transcripción y genera un plan de investigación (queries para Tavily).
        """
        prompt_text = """Actúa como un Arquitecto de Software Senior.
Analiza el siguiente texto (puede ser la transcripción de una reunión o un documento de requisitos). 
Tu objetivo es identificar dudas técnicas, decisiones de infraestructura pendientes (ej: qué DB usar, qué framework) o falta de información sobre librerías específicas.

Genera una lista de búsquedas (queries) para Google/Tavily que ayuden a aclarar estas dudas y construir un plan de implementación sólido.
IMPORTANTE: Genera un MÁXIMO de {max_queries} consultas de búsqueda para optimizar recursos. Prioriza solo lo más crítico.
Si el texto es muy claro y no requiere investigación externa, genera una lista vacía.

Contexto del Proyecto (Extracto o Completo):
{text}
"""
        # Usamos el text_splitter si es muy largo, pero para generar queries, 
        # a veces un resumen o los chunks iniciales bastan. 
        # Por simplicidad ahora, usaremos el texto filtrado si ya se tiene, o el raw.
        # Asumimos que le pasaremos un texto manejable o procesaremos chunks.
        # Para simplificar este paso HITL, tomaremos los primeros 20k caracteres o usaremos map-reduce si fuera necesario.
        # Dado el contexto del usuario, usaremos el modelo barato para filtrar primero si es necesario, 
        # pero para "Needs Analysis" el modelo bueno es mejor.
        
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | self.good_llm.with_structured_output(ResearchPlan)
        
        # Truncamos por seguridad si es raw text muy largo
        input_text = transcript_text[:50000] 
        
        try:
            result = chain.invoke({"text": input_text, "max_queries": max_queries})
            
            # HARD LIMIT: Enforce max queries to save Tavily credits
            if len(result.queries) > max_queries:
                logger.warning(f"LLM returned {len(result.queries)} queries. Truncating to {max_queries}.")
                result.queries = result.queries[:max_queries]
                
            return result.model_dump()
        except Exception as e:
            logger.error(f"Error generating research plan: {e}")
            return {"queries": []}

    def execute_research(self, queries: List[Dict[str, str]]) -> str:
        """
        Ejecuta las búsquedas en Tavily y devuelve un resumen formateado.
        """
        research_context = ""
        unique_queries = [q['query'] for q in queries if q.get('query')]
        
        return self._execute_research(unique_queries)

    def generate_architectural_plan(self, transcript_text: str, research_context: str) -> str:
        """
        Genera un plan de implementación en Markdown basado en la transcripción y la investigación.
        """
        prompt_text = """Actúa como un Arquitecto de Soluciones y Project Manager.
Tienes la información de contexto del proyecto (transcripción o documentos) y resultados de investigación técnica reciente.

Tu tarea es redactar un "Plan de Implementación y Arquitectura" (Documento Markdown).

El documento debe incluir:
1. **Resumen de Objetivos**: Qué se quiere construir.
2. **Propuesta de Stack Tecnológico**: Lenguajes, Frameworks, DBs (justificando decisiones con la investigación).
3. **Componentes Clave**: Módulos principales del sistema.
4. **Plan de Pasos**: Hoja de ruta sugerida.

Información de Investigación (Contexto Actualizado):
{research_context}

Información del Proyecto (Original):
{transcript}

Salida: Documento en formato Markdown.
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | self.good_llm | StrOutputParser()
        
        # Truncate transcript to fit context window if needed, prioritizing research + transcript beginning/end
        # Assuming model handles large context (Gemini/GPT-4o)
        return chain.invoke({
            "research_context": research_context if research_context else "No se requirió investigación adicional.",
            "transcript": transcript_text[:50000]
        })

    def extract_issues_from_plan(self, plan_text: str) -> Dict[str, Any]:
        """
        Genera issues de GitHub a partir del Plan de Implementación aprobado.
        """
        prompt_text = """Actúa como Project Manager.
A partir del siguiente Plan de Implementación aprobado por el usuario, desglosa el trabajo en Issues de GitHub concretos y accionables.

Plan de Implementación:
{plan}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | self.good_llm.with_structured_output(IssueList)
        
        try:
            result = chain.invoke({"plan": plan_text})
            return result.model_dump()
        except Exception as e:
            logger.error(f"Error extracting issues: {e}")
            return {"issues": []}

    def _execute_research(self, queries: list):
        research_context = ""
        
        for query in queries:
            logger.info(f"Tavily Searching: {query}")
            try:
                # Ejecutamos la búsqueda
                results = self.search_tool.invoke(query)
                
                # Tavily devuelve una lista de dicts. 
                # Si activamos 'include_answer', a veces viene aparte o en el primer resultado.
                # Procesamos la salida para que sea texto limpio para el LLM:
                research_context += f"\n\n## Resultados para: '{query}'\n"
                research_context += f"### Respuesta resumen: '{results.get('answer', 'No disponible')}'\n"

                results_list = results.get('results', [])
                for res in results_list:
                    # Estructura típica: {'url': '...', 'content': '...', 'score': ...}
                    content = res.get('content', '')
                    url = res.get('url', '')
                    research_context += f"\nFuente: {url}\nInfo: {content}\n"
                    
            except Exception as e:
                logger.error(f"Error buscando '{query}': {e}")
                
        return research_context

    def _get_filter_chain(self):
        prompt_text = """Actúa como un filtro inteligente de procesamiento de texto. Tu objetivo es leer el siguiente fragmento de una transcripción y extraer SOLAMENTE las partes que sean relevantes para el siguiente foco de negocio.

Foco / Criterio de Relevancia:
{criteria}

Instrucciones:
1. Extrae literalmente o resume fielmente las partes del diálogo relacionadas con el criterio.
2. Elimina saludos, divagaciones o temas irrelevantes.
3. Si no hay nada relevante en este fragmento, responde exactamente: 'SIN_CONTENIDO_RELEVANTE'.

Fragmento:
{text}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        return prompt | self.cheap_llm | StrOutputParser()

    def _get_analysis_chain(self):
        prompt_text = """Actúa como un Project Manager y Arquitecto de Software.
A continuación tienes una serie de textos filtrados de una reunión, ordenados cronológicamente.

Tu tarea es interpretar estos textos para identificar "Issues" o tareas de implementación necesarias para el sistema.

Contexto Filtrado:
{filtered_text}
"""
        prompt = ChatPromptTemplate.from_template(prompt_text)
        return prompt | self.good_llm.with_structured_output(IssueList)

    def _convert_history_to_messages(self, chat_history: List[Dict[str, str]]) -> List[Any]:
        messages = []
        for msg in chat_history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                messages.append(AIMessage(content=msg['content']))
        return messages

    def refine_issues(self, current_issues: List[Dict[str, Any]], user_query: str, chat_history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """
        Refina una lista de issues basándose en una query de lenguaje natural del usuario.
        """
        logger.info(f"Refining {len(current_issues)} issues with query: '{user_query}'")
        
        # Convert history
        history_messages = self._convert_history_to_messages(chat_history)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """Actúa como un Project Manager Senior.
Tienes una lista de issues actual y una solicitud de modificación del usuario.

Instrucciones:
1. Analiza la solicitud del usuario y el historial de la conversación.
2. Modifica, añade o elimina los issues según sea necesario para cumplir la solicitud.
3. Mantén intactos los issues que no necesiten cambios.
4. Devuelve la lista completa y actualizada.
"""),
            ("user", "Lista Actual de Issues:\n{current_issues}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Solicitud del Usuario:\n{user_query}")
        ])
        
        chain = prompt | self.good_llm.with_structured_output(IssueList)
        
        try:
            # Convert dicts back to string representation or just pass as json
            import json
            issues_str = json.dumps(current_issues, indent=2, ensure_ascii=False)
            
            final_result = chain.invoke({
                "current_issues": issues_str, 
                "user_query": user_query,
                "chat_history": history_messages
            })
            return final_result.model_dump()
        except Exception as e:
            logger.error(f"Error refining issues: {e}")
            raise e

    def refine_research_plan(self, current_queries: List[Dict[str, str]], user_query: str, chat_history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """
        Refina el plan de investigación (queries) basándose en una solicitud del usuario.
        """
        logger.info(f"Refining research plan with query: '{user_query}'")
        
        # Convert history
        history_messages = self._convert_history_to_messages(chat_history)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """Actúa como un Arquitecto de Software Senior y Experto en Búsquedas.
Tienes una lista de búsquedas (queries) planificadas y una solicitud de modificación del usuario.

Instrucciones:
1. Modifica, añade o elimina las queries según la solicitud del usuario y el historial.
2. Si el usuario pide investigar sobre un tema nuevo, añade las queries necesarias.
3. Mantén el formato de salida estructurado.

Genera la lista actualizada de Research Queries.
"""),
            ("user", "Queries Actuales:\n{current_queries}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Solicitud del Usuario:\n{user_query}")
        ])

        chain = prompt | self.good_llm.with_structured_output(ResearchPlan)
        
        try:
            # Pass queries as structured json string or just raw list
            import json
            queries_str = json.dumps(current_queries, indent=2, ensure_ascii=False)
            
            result = chain.invoke({
                "current_queries": queries_str, 
                "user_query": user_query,
                "chat_history": history_messages
            })
            return result.model_dump()
        except Exception as e:
            logger.error(f"Error refining research plan: {e}")
            raise e

    def refine_architectural_plan(self, current_plan: str, user_query: str, chat_history: List[Dict[str, str]] = []) -> str:
        """
        Refina el plan arquitectónico (texto markdown) basándose en una solicitud del usuario.
        """
        logger.info(f"Refining architectural plan with query: '{user_query}'")
        
        # Convert history
        history_messages = self._convert_history_to_messages(chat_history)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """Actúa como un Arquitecto de Soluciones Senior.
Tienes un borrador de un "Plan de Implementación y Arquitectura" y una solicitud de cambios del usuario.

Instrucciones:
1. Reescribe el plan incorporando los cambios, correcciones o adiciones solicitadas por el usuario, teniendo en cuenta el historial de conversación.
2. Mantén la estructura profesional del documento original si es posible (Resumen, Stack, Componentes, Pasos).
3. Devuelve EL TEXTO COMPLETO actualizado en Markdown.
"""),
            ("user", "Plan Actual (Markdown):\n{current_plan}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Solicitud del Usuario:\n{user_query}")
        ])

        chain = prompt | self.good_llm | StrOutputParser()
        
        try:
            return chain.invoke({
                "current_plan": current_plan, 
                "user_query": user_query,
                "chat_history": history_messages
            })
        except Exception as e:
            logger.error(f"Error refining architectural plan: {e}")
            raise e

    def process_transcript(self, transcript_text: str, criteria: str = "Requerimientos funcionales y reglas de negocio") -> Dict[str, Any]:
        # Phase 1: Chunking
        logger.info("Starting Phase 1: Chunking")
        list_chunks = self.text_splitter.split_text(transcript_text)
        chunks: List[(int, str)] = []
        for i, chunk in enumerate(list_chunks):
            chunks.append((i, chunk))
        logger.info(f"Created {len(chunks)} chunks")

        # Phase 2: Filtering (Map with Cheap LLM)
        logger.info(f"Starting Phase 2: Filtering with criteria: '{criteria}'")
        filter_chain = self._get_filter_chain()
        filtered_parts = []
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"Filtering chunk {i+1}/{len(chunks)}")
            result = filter_chain.invoke({"text": chunk[1], "criteria": criteria})
            if "SIN_CONTENIDO_RELEVANTE" not in result:
                filtered_parts.append(result)
            else:
                logger.debug(f"Chunk {i+1} discarded (irrelevant)")

        if not filtered_parts:
            logger.warning("No relevant content found in the transcript.")
            return {"issues": []}

        # Phase 3: Analysis (Reduce with Expensive LLM)
        logger.info("Starting Phase 3: Analysis and JSON Generation")
        analysis_chain = self._get_analysis_chain()
        concatenated_text = "\n---\n".join(filtered_parts)
        
        try:
            final_result = analysis_chain.invoke({"filtered_text": concatenated_text})
            return final_result.model_dump()
        except Exception as e:
            logger.error(f"Error parsing output: {e}")
            return {"error": "Failed to parse output", "details": str(e)}
