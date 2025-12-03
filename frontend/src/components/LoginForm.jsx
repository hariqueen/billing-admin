import React, { useState } from 'react';

const LoginForm = ({ onLogin }) => {
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // 하드코딩된 사용자 정보
  const users = {
    '2025040135': { name: '김하리', position: '주임' },
    '2025070184': { name: '김정웅', position: '이사' },
    '2025040003': { name: '허수빈', position: '과장' },
    '2023010297': { name: '장정근', position: '부장' },
    '2025070803': { name: '강주희', position: '부장' },
    '2025110391': { name: '이우진', position: '차장' }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!employeeId || !password) {
      setError('사번과 비밀번호를 입력해주세요.');
      return;
    }

    const user = users[employeeId];
    if (user) {
      // 성공적으로 로그인 (비밀번호도 함께 저장)
      onLogin({
        employeeId,
        name: user.name,
        position: user.position,
        password: password  // 비밀번호도 포함
      });
    } else {
      setError('등록되지 않은 사번입니다.');
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
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#0056b3'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#007bff'}
          >
            로그인
          </button>
        </form>


      </div>
    </div>
  );
};

export default LoginForm;
