# Datuvia

Datuvia es un AI Knowledge Hub: subís documentos a un workspace y hacés preguntas sobre su contenido. La respuesta se arma con RAG (retrieval-augmented generation): el sistema busca los fragmentos más cercanos a la pregunta y se los pasa a un modelo de lenguaje para que conteste solo con esa evidencia.

## Stack

- **API:** FastAPI y SQLModel
- **Base de datos:** PostgreSQL 16 con pgvector
- **Frontend:** React y TypeScript (Vite)
- **Infraestructura:** Docker Compose
- **Modelos de chat:** Gemini, Groq u OpenAI, en ese orden de prioridad
- **Embeddings:** OpenAI si hay clave; si no, un vector local para poder buscar sin costo

## Qué podés hacer

- Registrarte e iniciar sesión con JWT
- Crear workspaces y aislar los documentos de cada uno
- Subir `.pdf`, `.txt`, `.md`, `.csv` y `.json` (hasta 20 MB)
- Indexar el texto en fragmentos con el número de página
- Preguntar en un chat que cita las fuentes recuperadas y escribe la respuesta en vivo
- Seguir viendo el contexto recuperado si no hay ninguna clave de chat configurada

## Arquitectura

- **Procesamiento en segundo plano.** `POST /api/docs` guarda el archivo, crea el documento con estado `procesando` y responde 201 enseguida. Una `BackgroundTasks` de FastAPI extrae el texto, arma los fragmentos, calcula embeddings y pasa el estado a `listo`. Si el archivo no tiene texto, queda en `error`.
- **Streaming.** `POST /api/chat` responde `text/event-stream`. El primer evento trae las fuentes, después llega el texto del modelo token por token (`stream=true` en Gemini, Groq u OpenAI) y cierra con `done`.
- **Búsqueda híbrida.** Los fragmentos se ordenan combinando la distancia de coseno de pgvector (`<=>`) con la búsqueda de texto completo de PostgreSQL (`to_tsvector('spanish', ...)` y `to_tsquery`). El peso es 75 % semántico y 25 % por palabras clave.
- **CI.** En cada push a `main` o `master`, GitHub Actions instala el backend, levanta PostgreSQL con pgvector (`ankane/pgvector`) y corre `pytest` sobre `backend/tests`.
- **Memoria conversacional.** Cada chat pertenece a una `ChatSession` del workspace. `POST /api/chat` acepta un `session_id` opcional; si no llega, crea la sesión. La respuesta usa los últimos 5 mensajes.
- **Query rewriting.** Si hay historial, una llamada corta al proveedor reescribe la pregunta para que se entienda sola. Esa versión se usa en la búsqueda híbrida; la respuesta sigue la pregunta original y el contexto de la conversación.
- **Re-ranking.** Después de la búsqueda híbrida se descartan los fragmentos con similitud vectorial menor a 0.22, para no meter evidencia débil en el prompt.
- **Observabilidad.** Al cerrar el stream se guardan los dos mensajes con una estimación de tokens (o el total que informe el proveedor) y la latencia en milisegundos. La interfaz muestra “Generado en Xs” debajo de cada respuesta.

## Cómo levantarlo en local

Requisitos: Docker Desktop y Node.js 20 o superior.

1. Entrá a la carpeta del proyecto.

```bash
cd ai-knowledge-hub
```

2. Creá el archivo de entorno a partir del ejemplo.

```bash
copy .env.example .env
```

En macOS o Linux: `cp .env.example .env`.

3. Opcional: completá una clave en `.env` para que el chat genere respuestas con un modelo.

- `GEMINI_API_KEY` tiene prioridad
- si no hay Gemini, usa `GROQ_API_KEY`
- si no hay Groq, usa `OPENAI_API_KEY`

`.env` está en `.gitignore`. No lo subas al repositorio.

4. Levantá la base y la API.

```bash
docker compose up -d --build
```

- API: [http://localhost:8000](http://localhost:8000)
- Salud: [http://localhost:8000/health](http://localhost:8000/health)
- Postgres: `localhost:5433` (usuario `postgres`, base `knowledge_hub`)

5. En otra terminal, levantá el frontend.

```bash
cd frontend
npm install
npm run dev
```

Abrí la URL que muestra Vite, en general [http://localhost:5173](http://localhost:5173).

6. Creá una cuenta, un workspace, subí un documento y preguntá en **Chat IA**.

Para correr los tests de la API:

```bash
docker compose exec api pytest
```
