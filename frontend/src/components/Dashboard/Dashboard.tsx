import { useEffect, useState } from 'react';
import Workspaces, { type Workspace } from '../Workspaces/Workspaces';
import Documents from '../Documents/Documents';
import Chat from '../Chat/Chat';

interface UserData {
  id: string;
  email: string;
}

const TABS = [
  { id: 'workspaces', label: 'Workspaces' },
  { id: 'docs', label: 'Documentos' },
  { id: 'chat', label: 'Chat IA' },
] as const;

export default function Dashboard() {
  const [user, setUser] = useState<UserData | null>(null);
  const [activeTab, setActiveTab] = useState<'workspaces' | 'docs' | 'chat'>('workspaces');
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
    return <div className="auth-screen"><p className="loading">Cargando sesión...</p></div>;
  }

  const openTab = (tab: 'workspaces' | 'docs' | 'chat') => {
    setActiveTab(tab);
    setIsMobileMenuOpen(false);
  };

  return (
    <div className="shell">
      <header className="mobile-bar">
        <button
          type="button"
          className="menu-toggle"
          aria-label={isMobileMenuOpen ? 'Cerrar menú' : 'Abrir menú'}
          aria-expanded={isMobileMenuOpen}
          onClick={() => setIsMobileMenuOpen((open) => !open)}
        >
          <span className="menu-toggle-bar" />
          <span className="menu-toggle-bar" />
          <span className="menu-toggle-bar" />
        </button>
        <div className="brand">Datu<span>via</span></div>
      </header>
      {isMobileMenuOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Cerrar menú"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}
      <aside className={isMobileMenuOpen ? 'sidebar open' : 'sidebar'}>
        <div className="brand sidebar-brand">Datu<span>via</span></div>
        <nav className="nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? 'nav-btn active' : 'nav-btn'}
              onClick={() => openTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="workspace-pill">
            <div className="faint">Workspace activo</div>
            <strong>{selectedWorkspace ? selectedWorkspace.name : 'Ninguno'}</strong>
          </div>
          {user && (
            <div className="user-chip">
              <div className="faint">Sesión</div>
              <div>{user.email}</div>
            </div>
          )}
          <button type="button" className="btn btn-ghost" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="content">
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
