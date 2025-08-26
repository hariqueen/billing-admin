import React, { useState } from 'react';
import BillingAutomationAdmin from './components/BillingAutomationAdmin';
import LoginForm from './components/LoginForm';

function App() {
  const [user, setUser] = useState(null);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <div className="App">
      {user ? (
        <BillingAutomationAdmin 
          user={user} 
          onLogout={handleLogout} 
        />
      ) : (
        <LoginForm onLogin={handleLogin} />
      )}
    </div>
  );
}

export default App;