import React, { useState } from 'react';

const API_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:5001'
  : `http://${window.location.hostname}:5001`;

const LoginForm = ({ onLogin }) => {
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!employeeId || !password) {
      setError('사번과 비밀번호를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ employeeId, password })
      });

      const result = await response.json();
      if (!response.ok || !result.success) {
        setError(result.error || '로그인에 실패했습니다.');
        return;
      }

      onLogin({
        ...result.user,
        password // 자동화 화면에서 기존과 동일하게 사용
      });
    } catch (err) {
      console.error('로그인 요청 오류:', err);
      setError('로그인 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#f5f5f5',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
        width: '400px',
        maxWidth: '90vw'
      }}>
        <div style={{
          textAlign: 'center',
          marginBottom: '30px'
        }}>
          <h1 style={{
            fontSize: '24px',
            fontWeight: '600',
            color: '#333',
            margin: '0 0 8px 0'
          }}>
            청구 자동화 시스템
          </h1>
          <p style={{
            color: '#666',
            fontSize: '14px',
            margin: '0'
          }}>
            로그인하여 시스템을 이용하세요
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <input
              type="text"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              placeholder="사번"
              style={{
                width: '100%',
                padding: '12px 16px',
                border: '2px solid #e1e5e9',
                borderRadius: '8px',
                fontSize: '14px',
                outline: 'none',
                transition: 'border-color 0.2s',
                boxSizing: 'border-box'
              }}
              onFocus={(e) => e.target.style.borderColor = '#007bff'}
              onBlur={(e) => e.target.style.borderColor = '#e1e5e9'}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="비밀번호"
              style={{
                width: '100%',
                padding: '12px 16px',
                border: '2px solid #e1e5e9',
                borderRadius: '8px',
                fontSize: '14px',
                outline: 'none',
                transition: 'border-color 0.2s',
                boxSizing: 'border-box'
              }}
              onFocus={(e) => e.target.style.borderColor = '#007bff'}
              onBlur={(e) => e.target.style.borderColor = '#e1e5e9'}
            />
          </div>

          {error && (
            <div style={{
              backgroundColor: '#fee',
              color: '#c33',
              padding: '10px',
              borderRadius: '6px',
              fontSize: '14px',
              marginBottom: '20px',
              textAlign: 'center'
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: isLoading ? '#7eaee3' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => {
              if (!isLoading) e.target.style.backgroundColor = '#0056b3';
            }}
            onMouseOut={(e) => {
              if (!isLoading) e.target.style.backgroundColor = '#007bff';
            }}
          >
            {isLoading ? '로그인 중...' : '로그인'}
          </button>
        </form>


      </div>
    </div>
  );
};

export default LoginForm;
