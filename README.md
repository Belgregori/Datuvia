# Datuvia

AI Knowledge Hub. Los documentos se fragmentan, se embeben y se recuperan por workspace. El modelo responde solo con esa evidencia.

![Demo](https://github.com/user-attachments/assets/3e489700-5f97-4c0a-bd27-13bc4f1e644e)

<img width="1600" height="749" alt="Espacios de trabajo" src="https://github.com/user-attachments/assets/5a001f50-ca35-40ee-849c-e1f39341226e" />
<img width="1600" height="758" alt="Documentos" src="https://github.com/user-attachments/assets/3a5ce18b-9667-46d0-83b4-42f7bb358307" />
<img width="1600" height="759" alt="Chat" src="https://github.com/user-attachments/assets/8737c3eb-cd33-41b9-a9c5-12ae1231638c" />

## Arquitectura y Stack Tecnológico

**Backend.** Python, FastAPI, PostgreSQL 16 con pgvector, SQLAlchemy, Alembic y Docker Compose. La autenticación es JWT. El esquema viaja en revisiones de Alembic y se aplica al arrancar el contenedor (`alembic upgrade head`), no con `create_all` en el boot. Los proveedores de chat se eligen en este orden: Gemini, Groq, OpenAI. Los embeddings usan OpenAI si hay `OPENAI_API_KEY`; si no, un vector local de la misma dimensión permite buscar sin una API de embeddings paga.

**Frontend.** React 19, Vite, TypeScript, PWA instalable y layout mobile-first (navegación fuera de pantalla bajo 768px y el campo de pregunta fijo sobre el área segura).

## Características Enterprise (Key Features)

**Procesamiento asíncrono.** `POST /api/docs` guarda el archivo, inserta el documento en estado `procesando` y responde 201. Una `BackgroundTasks` de FastAPI extrae el texto (el PDF, página por página), arma los fragmentos, calcula embeddings y pasa el estado a `listo`. Si falla, queda en `error`. La tarea no reutiliza la sesión de la request.

**Búsqueda híbrida.** El ranking combina la distancia de coseno de pgvector (`<=>`) con full-text en español (`to_tsvector` / `to_tsquery`). El peso es 75 % similitud vectorial y 25 % `ts_rank` acotado. Solo entran documentos en estado `listo`. El `tsquery` se arma con tokens unidos por `&`, no con el texto crudo del usuario.

**Re-ranking contra evidencia débil.** Después de la búsqueda híbrida se descartan los fragmentos con similitud vectorial menor a 0.22 antes de llegar al prompt. Si no queda ninguno, el stream lo dice en lugar de responder con contexto ajeno.

**Streaming por SSE.** `POST /api/chat` responde `text/event-stream`. Los eventos son `session`, `sources`, `token` y `done` (`latency_ms`, `tokens_used`). La llamada al proveedor usa `stream=true`. El turno se persiste al cerrar el stream.

**Query rewriting.** Si la sesión tiene historial, una llamada corta sin streaming reescribe la pregunta para que se entienda sola. La búsqueda híbrida usa esa versión. La generación sigue viendo la pregunta original y los últimos cinco `ChatMessage`. Si la reescritura falla, la búsqueda usa la pregunta original.

## Guía de Instalación Local (Quickstart)

Hace falta Docker Desktop.

1. Cloná el repositorio y entrá a la carpeta.

```bash
git clone https://github.com/Belgregori/Datuvia.git
cd Datuvia
```

2. Creá el entorno a partir del ejemplo y definí `SECRET_KEY`. Es obligatoria y no tiene valor por defecto. Sumá `GEMINI_API_KEY`, `GROQ_API_KEY` u `OPENAI_API_KEY` si querés un modelo alojado. Sin ninguna, la API igual devuelve el contexto recuperado.

```bash
cp .env.example .env
```

3. Construí y levantá Postgres y la API.

```bash
docker compose up --build
```

API: `http://localhost:8000` (`GET /health`). La interfaz va aparte: `cd frontend && npm install && npm run dev`, y después abrí `http://localhost:5173`.

Para correr los tests de la API:

```bash
docker compose exec api pytest
```
