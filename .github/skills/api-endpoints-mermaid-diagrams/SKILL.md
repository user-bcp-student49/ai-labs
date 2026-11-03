---
name: api-endpoints-mermaid-diagrams
description: Analiza los endpoints de una API REST (OpenAPI, código o listado) y genera diagramas de secuencia y de componentes en formato Mermaid, con trazabilidad al endpoint de origen.
---

# Skill: API Endpoints -> Mermaid Sequence & Component Diagrams

## 1) Metadata
- **Skill ID:** api-endpoints-mermaid-diagrams
- **Version:** 0.1.0
- **Purpose:** Analizar endpoints de una API REST y generar diagramas de secuencia (flujos por endpoint) y de componentes (arquitectura y dependencias) en Mermaid, verificables contra la fuente.
- **Audience (roles):** Chapter/PO, Tech Lead, Backend, Frontend, QA, Cyber
- **When to use:** Al documentar una API existente, antes de revisar un diseño, al incorporar a alguien al equipo o al preparar un cambio que afecta varios endpoints.
- **When NOT to use:** APIs no REST (gRPC, GraphQL, mensajería pura) o cuando no hay ninguna fuente de endpoints disponible.
- **Sensitive inputs:** No incluyas datos reales de clientes, credenciales, secretos, tokens ni URLs internas no autorizadas. Usa hosts y ejemplos ficticios.
- **Expected output:** Markdown con bloques ```mermaid estructurado según la sección Output.

## 2) Inputs
Proporciona la información en este formato:

- **API name / business context (brief):**
- **Source of endpoints:** (OpenAPI/Swagger YAML o JSON, código de controladores/rutas, colección Postman o listado manual)
- **Endpoints to analyze:** (todos, o lista `MÉTODO /ruta`)
- **Known components:** (gateway, servicios, base de datos, cache, colas, IdP, APIs externas)
- **Auth model:** (OAuth2/JWT, API key, mTLS, ninguno)
- **Known technical constraints:** (stack, estándares, convenciones de nombres)
- **Diagram focus:** (flujo feliz, errores o ambos; nivel de detalle)
- **Known risks / dependencies:** (seguridad, servicios externos, equipos)

## 3) Output
Devuelve **solo** un documento Markdown con estas secciones y bullets:

1. **Summary**
    - API, número de endpoints analizados y fuente utilizada
2. **Inventario de endpoints**
    - Tabla: método, ruta, propósito, auth, códigos de respuesta, componentes que toca
3. **Diagrama de componentes** (`flowchart` en Mermaid)
    - Cliente, gateway, servicios, datastores y sistemas externos
    - Dirección de dependencias y protocolo en las aristas
    - Genera un archivo .md por cada enpodint en la carpeta /diagrams dentro del prouyecto.
4. **Diagramas de secuencia** (`sequenceDiagram` en Mermaid)
    - Uno por endpoint o por flujo agrupado
    - Incluye autenticación, llamadas a dependencias y al menos una respuesta de error relevante (`alt`/`opt`)
    - Genera un archivo .md por cada enpodint en la carpeta /diagrams dentro del prouyecto. 
5. **Trazabilidad**
    - Tabla que relaciona cada diagrama con sus endpoints y la referencia de la fuente (archivo/línea u operationId)
6. **Riesgos y observaciones**
    - Endpoints sin auth, cadenas de dependencias síncronas, acoplamientos, inconsistencias en la fuente
7. **Cómo validar**
    - Pasos concretos y evidencia a adjuntar
8. **Preguntas abiertas**
    - Elementos que no se pudieron inferir de la fuente y requieren aclaración

## 4) Constraints
- No inventes endpoints, componentes ni flujos: lo que no esté en la fuente va en **Supuestos** (si es razonable y declarado) o en **Preguntas abiertas**.
- Marca con `%% ASSUMPTION:` en el código Mermaid cualquier elemento inferido.
- No propongas herramientas fuera del stack permitido; usa solo Mermaid.
- No incluyas datos sensibles ni secretos; usa nombres genéricos (`Client`, `OrderService`).
- Sintaxis Mermaid válida: identificadores sin espacios ni caracteres especiales; etiquetas entre comillas si contienen paréntesis o símbolos.
- Cada diagrama de secuencia: máximo ~15 mensajes; si excede, divídelo por flujo.
- El diagrama de componentes: máximo ~15 nodos; agrupa con `subgraph` si es necesario.
- Mantén nombres de componentes consistentes entre todos los diagramas.
- Si hay más de 10 endpoints, agrupa por recurso y prioriza por criticidad.

## 5) Validation Rules
La salida es válida si:
- Incluye todas las secciones definidas en Output.
- Contiene exactamente un diagrama de componentes y al menos un diagrama de secuencia.
- Cada endpoint del alcance aparece en el inventario y en al menos un diagrama de secuencia, o se justifica su exclusión.
- Todos los bloques Mermaid renderizan sin error (verificado con Mermaid Live Editor, `mmdc` o vista previa de GitHub).
- Cada diagrama tiene al menos una fila en la tabla de Trazabilidad.
- Los diagramas de secuencia incluyen autenticación y al menos un camino de error.
- Los elementos inferidos están marcados como supuestos.
- No contiene datos sensibles ni secretos.

## 6) Evidence
Adjunta o referencia estos elementos en el PR o entrega:
- `SKILL.md` versionado.
- `examples/input.sample.md`.
- `examples/output.sample.md`.
- Captura o salida de render de los diagramas (por ejemplo, `mmdc -i output.md -o output.svg` o vista previa en GitHub).
- Tag de versión para el Skill, como `skill-api-mermaid-v0.1.0`.