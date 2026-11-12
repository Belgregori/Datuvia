import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Dashboard from './components/Dashboard/Dashboard';

export default function App() {
  const token = localStorage.getItem('token');

  if (token) {
    return <Dashboard />;
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', marginTop: '50px' }}>
      <Login />
      <Register />
    </div>
  );
}