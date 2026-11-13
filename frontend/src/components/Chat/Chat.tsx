import { useEffect, useRef, useState } from 'react';
import { type Workspace } from '../Workspaces/Workspaces';

interface Source {
  document_id: string;
  title: string;
  page_number: number | null;
  score: number;
  excerpt: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  latencyMs?: number | null;
}

interface ChatSessionItem {
  id: string;
  title: string;
}

interface ChatProps {
  selectedWorkspace: Workspace | null;
}

export default function Chat({ selectedWorkspace }: ChatProps) {
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const activeSessionRef = useRef<string | null>(null);

  useEffect(() => {
    activeSessionRef.current = activeSessionId;
  }, [activeSessionId]);

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  });

  const loadSessions = async (workspaceId: string) => {
    const response = await fetch(`http://localhost:8000/api/chat/sessions/${workspaceId}`, {
      headers: authHeaders(),
    });
    if (!response.ok) return;
    const data: ChatSessionItem[] = await response.json();
    setSessions(data);
  };

  const loadMessages = async (sessionId: string) => {
    const response = await fetch(`http://localhost:8000/api/chat/sessions/${sessionId}/messages`, {
      headers: authHeaders(),
    });
    if (!response.ok) {
      setError('No se pudo cargar la conversación');
      return;
    }
    const data: Array<{ role: 'user' | 'assistant'; content: string; latency_ms: number | null }> = await response.json();
    setMessages(data.map((message) => ({
      role: message.role,
      content: message.content,
      latencyMs: message.latency_ms,
    })));
  };

  useEffect(() => {
    setMessages([]);
    setError('');
    setQuestion('');
    setActiveSessionId(null);
    if (selectedWorkspace) {
      loadSessions(selectedWorkspace.id).catch(() => setError('No se pudieron cargar las conversaciones'));
    } else {
      setSessions([]);
    }
  }, [selectedWorkspace?.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = question.trim();
    if (!text || !selectedWorkspace || loading) return;

    setMessages((current) => [...current, { role: 'user', content: text }, { role: 'assistant', content: '' }]);
    setQuestion('');
    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          workspace_id: selectedWorkspace.id,
          question: text,
          session_id: activeSessionRef.current,
        }),
      });

      if (!response.ok || !response.body) {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || 'No se pudo obtener una respuesta');
        setMessages((current) => current.slice(0, -1));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let answer = '';
      let sources: Source[] = [];
      let latencyMs: number | null = null;

      const publish = () => {
        setMessages((current) => {
          const next = [...current];
          const last = next.length - 1;
          if (next[last]?.role === 'assistant') {
            next[last] = { role: 'assistant', content: answer, sources, latencyMs };
          }
          return next;
        });
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
          const line = frame.split('\n').find((item) => item.startsWith('data:'));
          if (!line) continue;
          const event = JSON.parse(line.slice(5).trim()) as {
            type: string;
            text?: string;
            sources?: Source[];
            session_id?: string;
            latency_ms?: number;
          };
          if (event.type === 'session' && event.session_id) {
            setActiveSessionId(event.session_id);
          }
          if (event.type === 'sources' && event.sources) sources = event.sources;
          if (event.type === 'token' && event.text) answer += event.text;
          if (event.type === 'done' && event.latency_ms != null) latencyMs = event.latency_ms;
          publish();
        }
      }
      await loadSessions(selectedWorkspace.id);
    } catch (err) {
      console.error('Error en el chat:', err);
      setError('Error de conexión con el servidor');
    } finally {
      setLoading(false);
    }
  };

  if (!selectedWorkspace) {
    return (
      <section className="stack">
        <header className="page-head">
          <h2>Chat con tus documentos</h2>
        </header>
        <p className="empty">Seleccioná o creá un workspace primero para hacer preguntas sobre tus documentos.</p>
      </section>
    );
  }

  return (
    <div className="chat-shell">
      <aside className="session-panel">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            setActiveSessionId(null);
            setMessages([]);
            setError('');
          }}
        >
          Nueva conversación
        </button>
        <div className="session-list">
          {sessions.length === 0 ? (
            <p className="faint">Sin conversaciones</p>
          ) : (
            sessions.map((item) => (
              <button
                key={item.id}
                type="button"
                className={item.id === activeSessionId ? 'session-item active' : 'session-item'}
                onClick={() => {
                  setActiveSessionId(item.id);
                  setError('');
                  loadMessages(item.id);
                }}
              >
                {item.title}
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="chat">
        <header className="page-head">
          <h2>Chat en “{selectedWorkspace.name}”</h2>
          <p className="muted">Las respuestas usan el historial de esta conversación.</p>
        </header>

        <div className="chat-thread">
          {messages.length === 0 && (
            <p className="empty">Preguntá algo sobre los documentos de este workspace.</p>
          )}
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={message.role === 'user' ? 'bubble bubble-user' : 'bubble bubble-assistant'}
            >
              <div className="bubble-label">{message.role === 'user' ? 'Vos' : 'Asistente'}</div>
              <div>{message.content}</div>
              {message.sources && message.sources.length > 0 && (
                <div className="pills">
                  {message.sources.map((source, sourceIndex) => (
                    <span
                      key={`${source.document_id}-${source.page_number}-${sourceIndex}`}
                      className="pill"
                      title={source.excerpt}
                    >
                      {source.title}
                      {source.page_number != null && ` · p. ${source.page_number}`}
                    </span>
                  ))}
                </div>
              )}
              {message.role === 'assistant' && message.latencyMs != null && (
                <div className="latency">Generado en {(message.latencyMs / 1000).toFixed(1)}s</div>
              )}
            </article>
          ))}
          {loading && <p className="loading">Buscando en los documentos...</p>}
          <div ref={endRef} />
        </div>

        <form className="chat-composer" onSubmit={handleSubmit}>
          <textarea
            className="input"
            rows={2}
            placeholder="Escribí tu pregunta y presioná Enter"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
            disabled={loading}
          />
          <button className="btn btn-primary" type="submit" disabled={loading || !question.trim()}>
            {loading ? 'Enviando...' : 'Preguntar'}
          </button>
        </form>
        {error && <div className="error">{error}</div>}
      </section>
    </div>
  );
}
