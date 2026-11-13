import { useEffect, useState } from 'react';

export interface Workspace {
  id: string;
  name: string;
}

interface WorkspacesProps {
  selectedWorkspace: Workspace | null;
  onSelectWorkspace: (workspace: Workspace | null) => void;
}

export default function Workspaces({ selectedWorkspace, onSelectWorkspace }: WorkspacesProps) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');

  const fetchWorkspaces = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/workspaces', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data: Workspace[] = await response.json();
        setWorkspaces(data);
        if (!selectedWorkspace && data.length > 0) {
          onSelectWorkspace(data[0]);
        }
      } else {
        setError('No se pudieron cargar los workspaces');
      }
    } catch (err) {
      console.error('Error cargando workspaces:', err);
      setError('Error de conexión con el servidor');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/workspaces', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newName }),
      });

      if (response.ok) {
        const created: Workspace = await response.json();
        setWorkspaces([created, ...workspaces]);
        onSelectWorkspace(created);
        setNewName('');
      } else {
        setError('No se pudo crear el workspace');
      }
    } catch (err) {
      console.error('Error creando workspace:', err);
      setError('Error de conexión con el servidor');
    }
  };

  const handleDelete = async (id: string) => {
    setError('');
    try {
      const response = await fetch(`http://localhost:8000/api/workspaces/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const updated = workspaces.filter((w) => w.id !== id);
        setWorkspaces(updated);
        if (selectedWorkspace?.id === id) {
          onSelectWorkspace(updated.length > 0 ? updated[0] : null);
        }
      } else {
        setError('No se pudo eliminar el workspace');
      }
    } catch (err) {
      console.error('Error eliminando workspace:', err);
      setError('Error de conexión con el servidor');
    }
  };

  return (
    <section className="stack">
      <header className="page-head">
        <h2>Espacios de trabajo</h2>
        <p className="muted">Cada workspace agrupa los documentos sobre los que podés preguntar.</p>
      </header>

      <form className="row panel" onSubmit={handleCreate}>
        <input
          className="input"
          type="text"
          placeholder="Nombre del nuevo workspace"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          required
        />
        <button className="btn btn-primary" type="submit">Crear</button>
      </form>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <p className="loading">Cargando espacios de trabajo...</p>
      ) : workspaces.length === 0 ? (
        <p className="empty">No tenés workspaces creados todavía.</p>
      ) : (
        <ul className="card-list">
          {workspaces.map((ws) => {
            const isSelected = selectedWorkspace?.id === ws.id;
            return (
              <li key={ws.id} className={isSelected ? 'card active' : 'card'}>
                <div>
                  <div className="card-title">{ws.name}</div>
                  {isSelected && <div className="meta"><span className="badge badge-md">Activo</span></div>}
                </div>
                <div className="row">
                  {!isSelected && (
                    <button type="button" className="btn btn-ghost" onClick={() => onSelectWorkspace(ws)}>
                      Seleccionar
                    </button>
                  )}
                  <button type="button" className="btn btn-danger" onClick={() => handleDelete(ws.id)}>
                    Eliminar
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
