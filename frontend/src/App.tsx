import { useState } from 'react';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Dashboard from './components/Dashboard/Dashboard';

export default function App() {
  const token = localStorage.getItem('token');
  const [mode, setMode] = useState<'login' | 'register'>('login');

  if (token) {
    return <Dashboard />;
  }

  return (
    <div className="auth-screen">
      <section className="auth-card">
        <div>
          <div className="brand">Datu<span>via</span></div>
          <p className="muted">Preguntale a tus documentos.</p>
        </div>
        <div className="tabs" role="tablist">
          <button
            type="button"
            className={mode === 'login' ? 'tab active' : 'tab'}
            onClick={() => setMode('login')}
          >
            Iniciar sesión
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'tab active' : 'tab'}
            onClick={() => setMode('register')}
          >
            Registrarse
          </button>
        </div>
        {mode === 'login' ? <Login /> : <Register />}
      </section>
    </div>
  );
}
