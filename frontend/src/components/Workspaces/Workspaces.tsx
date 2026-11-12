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
      }
    } catch (error) {
      console.error('Error cargando workspaces:', error);
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
      }
    } catch (error) {
      console.error('Error creando workspace:', error);
    }
  };

  const handleDelete = async (id: string) => {
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
      }
    } catch (error) {
      console.error('Error eliminando workspace:', error);
    }
  };

  if (loading) return <p>Cargando espacios de trabajo...</p>;

  return (
    <div>
      <h2>Espacios de Trabajo</h2>

      <form onSubmit={handleCreate} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input
          type="text"
          placeholder="Nombre del nuevo workspace"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          required
          style={{ flex: 1, padding: '8px' }}
        />
        <button type="submit" style={{ padding: '8px 16px' }}>
          Crear
        </button>
      </form>

      {workspaces.length === 0 ? (
        <p style={{ color: '#888' }}>No tenés workspaces creados todavía.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {workspaces.map((ws) => {
            const isSelected = selectedWorkspace?.id === ws.id;
            return (
              <li
                key={ws.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px',
                  border: isSelected ? '2px solid #646cff' : '1px solid #333',
                  borderRadius: '6px',
                }}
              >
                <div>
                  <strong>{ws.name}</strong>
                  {isSelected && <span style={{ marginLeft: '10px', fontSize: '0.8rem', color: '#646cff' }}>(Activo)</span>}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {!isSelected && (
                    <button onClick={() => onSelectWorkspace(ws)}>Seleccionar</button>
                  )}
                  <button onClick={() => handleDelete(ws.id)} style={{ color: '#ff6b6b' }}>
                    Eliminar
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}