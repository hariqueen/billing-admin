import React, { useState, useEffect } from 'react';
import BillingAutomationAdmin from './components/BillingAutomationAdmin';
import LoginForm from './components/LoginForm';

function App() {
  const [user, setUser] = useState(() => {
    // localStorage에서 사용자 정보 불러오기
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const handleLogin = (userData) => {
    // 로그인 시 localStorage에 사용자 정보 저장
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    // 로그아웃 시 localStorage에서 사용자 정보 제거
    localStorage.removeItem('user');
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