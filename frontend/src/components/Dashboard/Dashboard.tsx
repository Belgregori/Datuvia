import { useEffect, useState } from 'react';
import Workspaces, { type Workspace } from '../Workspaces/Workspaces';
import Documents from '../Documents/Documents';
import Chat from '../Chat/Chat';

interface UserData {
  id: string;
  email: string;
}

export default function Dashboard() {
  const [user, setUser] = useState<UserData | null>(null);
  const [activeTab, setActiveTab] = useState<'workspaces' | 'docs' | 'chat'>('workspaces');
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        window.location.reload();
        return;
      }

      try {
        const response = await fetch('http://localhost:8000/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.ok) {
          const data = await response.json();
          setUser(data);
        } else {
          localStorage.removeItem('token');
          window.location.reload();
        }
      } catch (error) {
        console.error('Error validando sesión:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.reload();
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Cargando sesión...</div>;
  }

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #333', paddingBottom: '15px', marginBottom: '20px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Datuvia</h1>
          {user && <small style={{ color: '#888' }}>Sesión iniciada como: {user.email}</small>}
          {selectedWorkspace && (
            <div style={{ fontSize: '0.85rem', color: '#646cff', marginTop: '4px' }}>
              Workspace activo: <strong>{selectedWorkspace.name}</strong>
            </div>
          )}
        </div>
        <button onClick={handleLogout} style={{ padding: '8px 14px', cursor: 'pointer' }}>
          Cerrar sesión
        </button>
      </header>

      <nav style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button
          onClick={() => setActiveTab('workspaces')}
          style={{ fontWeight: activeTab === 'workspaces' ? 'bold' : 'normal' }}
        >
          Workspaces
        </button>
        <button
          onClick={() => setActiveTab('docs')}
          style={{ fontWeight: activeTab === 'docs' ? 'bold' : 'normal' }}
        >
          Documentos
        </button>
        <button
          onClick={() => setActiveTab('chat')}
          style={{ fontWeight: activeTab === 'chat' ? 'bold' : 'normal' }}
        >
          Chat IA
        </button>
      </nav>

      <main style={{ padding: '20px', border: '1px solid #333', borderRadius: '8px' }}>
        {activeTab === 'workspaces' && (
          <Workspaces
            selectedWorkspace={selectedWorkspace}
            onSelectWorkspace={setSelectedWorkspace}
          />
        )}

        {activeTab === 'docs' && (
          <Documents selectedWorkspace={selectedWorkspace} />
        )}

        {activeTab === 'chat' && (
          <Chat selectedWorkspace={selectedWorkspace} />
        )}
      </main>
    </div>
  );
}