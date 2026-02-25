import React, { useState } from 'react';
import { ArrowLeft, Save } from 'lucide-react';

const API_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:5001'
  : `http://${window.location.hostname}:5001`;

const UserProfileManager = ({ user, onBack, onUserUpdated }) => {
  const [position, setPosition] = useState(user?.position || '');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const payload = {};

    if (position && position !== user?.position) {
      payload.position = position;
    }
    if (password) {
      if (password.length < 4) {
        alert('비밀번호는 4자 이상 입력해주세요.');
        return;
      }
      payload.password = password;
    }

    if (Object.keys(payload).length === 0) {
      alert('변경된 항목이 없습니다.');
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/admin-users/${user.employeeId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const result = await response.json();

      if (!response.ok || !result.success) {
        alert(result.error || '계정 수정에 실패했습니다.');
        return;
      }

      const updatedUser = {
        ...user,
        ...result.user
      };

      if (password) {
        updatedUser.password = password;
      }

      onUserUpdated(updatedUser);
      setPassword('');
      alert('계정 정보가 수정되었습니다.');
    } catch (error) {
      console.error('계정 수정 오류:', error);
      alert('계정 수정 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            뒤로가기
          </button>
          <h1 className="text-2xl font-bold text-gray-900">내 계정</h1>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">이름</label>
            <input
              value={user?.name || ''}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">사번</label>
            <input
              value={user?.employeeId || ''}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">직급</label>
            <input
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="직급을 입력하세요"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">새 비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="변경할 때만 입력"
            />
            <p className="text-xs text-gray-500 mt-1">초기 비밀번호는 1234입니다.</p>
          </div>

          <div className="pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              {saving ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfileManager;
