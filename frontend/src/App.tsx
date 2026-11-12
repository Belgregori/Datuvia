import Login from './components/Auth/Login';
import Register from './components/Auth/Register';

function App() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: '50px', marginTop: '50px' }}>
      <Login />
      <Register />
    </div>
  );
}

export default App;