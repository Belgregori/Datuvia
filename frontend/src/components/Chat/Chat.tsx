import { useEffect, useState } from 'react';
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
}

interface ChatProps {
  selectedWorkspace: Workspace | null;
}

export default function Chat({ selectedWorkspace }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setMessages([]);
    setError('');
    setQuestion('');
  }, [selectedWorkspace?.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = question.trim();
    if (!text || !selectedWorkspace || loading) return;

    setMessages((current) => [...current, { role: 'user', content: text }]);
    setQuestion('');
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          workspace_id: selectedWorkspace.id,
          question: text,
        }),
      });

      if (response.ok) {
        const data: { answer: string; sources: Source[] } = await response.json();
        setMessages((current) => [
          ...current,
          { role: 'assistant', content: data.answer, sources: data.sources },
        ]);
      } else {
        const errData = await response.json();
        setError(errData.detail || 'No se pudo obtener una respuesta');
      }
    } catch (err) {
      console.error('Error en el chat:', err);
      setError('Error de conexión con el servidor');
    } finally {
      setLoading(false);
    }
  };

  if (!selectedWorkspace) {
    return (
      <div>
        <h2>Chat con tus Documentos</h2>
        <p style={{ color: '#888' }}>
          Seleccioná o creá un Workspace primero para hacer preguntas sobre tus documentos.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2>Chat en "{selectedWorkspace.name}"</h2>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          marginBottom: '16px',
          minHeight: '180px',
        }}
      >
        {messages.length === 0 ? (
          <p style={{ color: '#888' }}>
            Preguntá algo sobre los documentos de este workspace.
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              style={{
                padding: '12px',
                border: '1px solid #333',
                borderRadius: '6px',
                alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                background: message.role === 'user' ? '#1a1a2e' : 'transparent',
              }}
            >
              <div style={{ fontSize: '0.75rem', color: '#888', marginBottom: '6px' }}>
                {message.role === 'user' ? 'Vos' : 'Asistente'}
              </div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
              {message.sources && message.sources.length > 0 && (
                <ul
                  style={{
                    listStyle: 'none',
                    padding: 0,
                    margin: '10px 0 0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  {message.sources.map((source) => (
                    <li
                      key={`${source.document_id}-${source.page_number}`}
                      style={{
                        fontSize: '0.85rem',
                        color: '#aaa',
                        borderTop: '1px solid #333',
                        paddingTop: '8px',
                      }}
                    >
                      <strong>{source.title}</strong>
                      {source.page_number != null && ` · fragmento ${source.page_number}`}
                      {' · '}
                      score {source.score}
                      <div>{source.excerpt}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))
        )}
        {loading && <p style={{ color: '#888' }}>Buscando en los documentos...</p>}
      </div>

      <form
        onSubmit={handleSubmit}
        style={{ display: 'flex', gap: '10px', alignItems: 'center' }}
      >
        <input
          type="text"
          placeholder="Escribí tu pregunta"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
          style={{ flex: 1, padding: '8px' }}
        />
        <button type="submit" disabled={loading || !question.trim()} style={{ padding: '8px 16px' }}>
          {loading ? 'Enviando...' : 'Preguntar'}
        </button>
      </form>
      {error && <small style={{ color: '#ff6b6b' }}>{error}</small>}
    </div>
  );
}
