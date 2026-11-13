import { useEffect, useState } from 'react';
import { type Workspace } from '../Workspaces/Workspaces';

interface DocumentItem {
  id: string;
  title: string;
  file_type: string;
  chunk_count: number;
  status: string;
}

interface DocumentsProps {
  selectedWorkspace: Workspace | null;
}

function typeClass(fileType: string) {
  const key = fileType.replace('.', '').toLowerCase();
  if (key === 'pdf' || key === 'txt' || key === 'md' || key === 'csv' || key === 'json') {
    return `badge badge-${key}`;
  }
  return 'badge';
}

export default function Documents({ selectedWorkspace }: DocumentsProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');

  const fetchDocuments = async (silent = false) => {
    if (!selectedWorkspace) return;
    if (!silent) {
      setLoading(true);
      setError('');
    }
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
      } else if (!silent) {
        setError('No se pudieron cargar los documentos');
      }
    } catch (err) {
      console.error('Error cargando documentos:', err);
      if (!silent) setError('Error de conexión con el servidor');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedWorkspace) {
      fetchDocuments();
    } else {
      setDocuments([]);
    }
  }, [selectedWorkspace]);

  useEffect(() => {
    if (!documents.some((doc) => doc.status === 'procesando')) return;
    const timer = window.setInterval(() => {
      fetchDocuments(true);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [documents, selectedWorkspace]);

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
      } else {
        setError('No se pudo eliminar el documento');
      }
    } catch (err) {
      console.error('Error eliminando documento:', err);
      setError('Error de conexión con el servidor');
    }
  };

  if (!selectedWorkspace) {
    return (
      <section className="stack">
        <header className="page-head">
          <h2>Documentos</h2>
        </header>
        <p className="empty">Seleccioná o creá un workspace primero para subir y ver tus documentos.</p>
      </section>
    );
  }

  return (
    <section className="stack">
      <header className="page-head">
        <h2>Documentos en “{selectedWorkspace.name}”</h2>
        <p className="muted">Los archivos se dividen en fragmentos y quedan listos para el chat.</p>
      </header>

      <form className="stack panel" onSubmit={handleUpload}>
        <input
          className="input"
          type="text"
          placeholder="Título opcional (si lo dejás vacío usa el nombre del archivo)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="row">
          <input
            id="doc-file-input"
            className="file-input"
            type="file"
            accept=".pdf,.txt,.md,.csv,.json"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />
          <button className="btn btn-primary" type="submit" disabled={uploading || !file}>
            {uploading ? 'Procesando...' : 'Subir archivo'}
          </button>
        </div>
        <p className="faint">Formatos permitidos: .pdf, .txt, .md, .csv, .json (máx. 20 MB)</p>
        {error && <div className="error">{error}</div>}
      </form>

      {loading ? (
        <p className="loading">Cargando documentos...</p>
      ) : documents.length === 0 ? (
        <p className="empty">No hay documentos cargados en este workspace.</p>
      ) : (
        <ul className="card-list">
          {documents.map((doc) => (
            <li key={doc.id} className="card">
              <div>
                <div className="card-title">{doc.title}</div>
                <div className="meta">
                  <span className={typeClass(doc.file_type)}>{doc.file_type.replace('.', '') || 'archivo'}</span>
                  <span className="badge badge-count">{doc.chunk_count} fragmentos</span>
                  {doc.status === 'procesando' ? (
                    <span className="badge badge-md"><span className="spinner" /> Procesando</span>
                  ) : doc.status === 'error' ? (
                    <span className="badge badge-pdf">Error</span>
                  ) : (
                    <span className="badge badge-csv">Listo</span>
                  )}
                </div>
              </div>
              <button type="button" className="btn btn-danger" onClick={() => handleDelete(doc.id)}>
                Eliminar
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
