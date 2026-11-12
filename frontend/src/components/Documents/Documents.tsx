import { useEffect, useState } from 'react';
import { type Workspace } from '../Workspaces/Workspaces';

interface DocumentItem {
  id: string;
  title: string;
  file_type: string;
  chunk_count: number;
}

interface DocumentsProps {
  selectedWorkspace: Workspace | null;
}

export default function Documents({ selectedWorkspace }: DocumentsProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');

  const fetchDocuments = async () => {
    if (!selectedWorkspace) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(
        `http://localhost:8000/api/docs?workspace_id=${selectedWorkspace.id}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (response.ok) {
        const data: DocumentItem[] = await response.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Error cargando documentos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedWorkspace) {
      fetchDocuments();
    } else {
      setDocuments([]);
    }
  }, [selectedWorkspace]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !selectedWorkspace) return;

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('workspace_id', selectedWorkspace.id);
    if (title.trim()) {
      formData.append('title', title.trim());
    }

    try {
      const response = await fetch('http://localhost:8000/api/docs', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        const created: DocumentItem = await response.json();
        setDocuments([created, ...documents]);
        setFile(null);
        setTitle('');
        const fileInput = document.getElementById('doc-file-input') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
      } else {
        const errData = await response.json();
        setError(errData.detail || 'Error al subir el documento');
      }
    } catch (err) {
      console.error('Error subiendo documento:', err);
      setError('Error de conexión con el servidor');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/docs/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setDocuments(documents.filter((doc) => doc.id !== id));
      }
    } catch (err) {
      console.error('Error eliminando documento:', err);
    }
  };

  if (!selectedWorkspace) {
    return (
      <div>
        <h2>Mis Documentos</h2>
        <p style={{ color: '#888' }}>
          Seleccioná o creá un Workspace primero para subir y ver tus documentos.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2>Documentos en "{selectedWorkspace.name}"</h2>

      <form
        onSubmit={handleUpload}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          marginBottom: '20px',
          padding: '15px',
          border: '1px solid #333',
          borderRadius: '6px',
        }}
      >
        <input
          type="text"
          placeholder="Título opcional (si lo dejás vacío usa el nombre del archivo)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ padding: '8px' }}
        />
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            id="doc-file-input"
            type="file"
            accept=".pdf,.txt,.md,.csv,.json"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={uploading || !file} style={{ padding: '8px 16px' }}>
            {uploading ? 'Procesando...' : 'Subir archivo'}
          </button>
        </div>
        <small style={{ color: '#888' }}>Formatos permitidos: .pdf, .txt, .md, .csv, .json (máx. 2 MB)</small>
        {error && <small style={{ color: '#ff6b6b' }}>{error}</small>}
      </form>

      {loading ? (
        <p>Cargando documentos...</p>
      ) : documents.length === 0 ? (
        <p style={{ color: '#888' }}>No hay documentos cargados en este workspace.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {documents.map((doc) => (
            <li
              key={doc.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '12px',
                border: '1px solid #333',
                borderRadius: '6px',
              }}
            >
              <div>
                <strong>{doc.title}</strong>
                <div style={{ fontSize: '0.85rem', color: '#888' }}>
                  Tipo: {doc.file_type} • Fragmentos indexados: {doc.chunk_count}
                </div>
              </div>
              <button onClick={() => handleDelete(doc.id)} style={{ color: '#ff6b6b' }}>
                Eliminar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}