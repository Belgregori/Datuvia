import { useState } from 'react';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        setSuccess('Cuenta creada. Ahora podés iniciar sesión.');
        setPassword('');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'No se pudo registrar');
      }
    } catch (err) {
      console.error('Error de conexión:', err);
      setError('Error de conexión con el servidor');
    }
  };

  return (
    <form className="stack" onSubmit={handleSubmit}>
      <label className="field">
        <span>Email</span>
        <input
          className="input"
          type="email"
          placeholder="vos@empresa.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </label>
      <label className="field">
        <span>Contraseña</span>
        <input
          className="input"
          type="password"
          placeholder="Mínimo 8 caracteres"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error && <div className="error">{error}</div>}
      {success && <div className="ok">{success}</div>}
      <button className="btn btn-primary" type="submit">Crear cuenta</button>
    </form>
  );
}
