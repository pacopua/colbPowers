from pydantic import BaseModel, Field
from typing import List, Literal

class Issue(BaseModel):
    title: str = Field(description="Título breve del issue")
    description: str = Field(description="Descripción técnica detallada de la tarea a realizar")
    priority: Literal["High", "Medium", "Low"] = Field(description="Nivel de prioridad de la tarea")
    type: Literal["Feature", "Bug", "Task"] = Field(description="Tipo de issue (Funcionalidad, Error, Tarea)")

class IssueList(BaseModel):
    issues: List[Issue]

class ResearchQuery(BaseModel):
    query: str = Field(description="Pregunta de búsqueda optimizada para un motor de búsqueda web (Tavily)")
    rationale: str = Field(description="Breve explicación de por qué es necesaria esta búsqueda")

class ResearchPlan(BaseModel):
    queries: List[ResearchQuery] = Field(description="Lista de búsquedas a realizar")
