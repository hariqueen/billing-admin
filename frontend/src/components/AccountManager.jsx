import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, Save, ArrowLeft, Plus, Trash2 } from 'lucide-react';

// API URL을 환경에 따라 자동으로 선택
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5001'
  : `http://${window.location.hostname}:5001`;

const AccountManager = ({ onBack }) => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPasswords, setShowPasswords] = useState({});
  const [editingAccount, setEditingAccount] = useState(null);
  const [viewType, setViewType] = useState('project'); // 'project' 또는 'llm'
  const [newAccount, setNewAccount] = useState({
    company_name: '',
    account_type: 'sms',
    url: '',
    username: '',
    password: '',
    status: 'active'
  });

  // 계정을 회사별로 그룹화하는 함수
  const groupAccountsByCompany = (accounts) => {
    const grouped = {};
    accounts.forEach(account => {
      if (!grouped[account.company_name]) {
        grouped[account.company_name] = [];
      }
      grouped[account.company_name].push(account);
    });
    return grouped;
  };

  // Firebase에서 계정 정보 가져오기
  const fetchAccounts = async () => {
    try {
      console.log('계정 정보 로드 시작...');
      const response = await fetch(`${API_URL}/api/accounts`);
      console.log('API 응답:', response);
      
      if (response.ok) {
        const data = await response.json();
        console.log('받은 데이터:', data);
        setAccounts(data.accounts || []);
      } else {
        const errorData = await response.json();
        console.error('API 오류:', errorData);
        
        // 임시 시뮬레이션 데이터 (Firebase 연결 실패 시)
        console.log('시뮬레이션 데이터 로드...');
        const simulationData = [
          {
            id: '1',
            company_name: '앤하우스',
            account_type: 'sms',
            site_url: 'https://ann.metaics.co.kr:8443/jsp/login.jsp',
            username: 'system',
            password: 'test1234@',
            status: 'active'
          },
          {
            id: '2',
            company_name: '앤하우스',
            account_type: 'call',
            site_url: 'https://ann.metahub.co.kr/',
            username: '16099',
            password: '16099',
            status: 'active'
          },
          {
            id: '3',
            company_name: '디싸이더스/애드프로젝트',
            account_type: 'sms',
            site_url: 'https://deciders.metahub.co.kr/jsp/login.jsp',
            username: 'system',
            password: 'test1234$',
            status: 'active'
          }
        ];
        setAccounts(simulationData);
      }
    } catch (error) {
      console.error('계정 정보 로드 실패:', error);
      
      // 네트워크 오류 시에도 시뮬레이션 데이터 로드
      console.log('네트워크 오류로 시뮬레이션 데이터 로드...');
      const simulationData = [
        {
          id: '1',
          company_name: '앤하우스',
          account_type: 'sms',
          site_url: 'https://ann.metaics.co.kr:8443/jsp/login.jsp',
          username: 'system',
          password: 'test1234@',
          status: 'active'
        },
        {
          id: '2',
          company_name: '앤하우스',
          account_type: 'call',
          site_url: 'https://ann.metahub.co.kr/',
          username: '16099',
          password: '16099',
          status: 'active'
        }
      ];
      setAccounts(simulationData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  // 비밀번호 표시/숨김 토글
  const togglePasswordVisibility = (accountId) => {
    setShowPasswords(prev => ({
      ...prev,
      [accountId]: !prev[accountId]
    }));
  };

  // 계정 추가
  const handleAddAccount = () => {
    setEditingAccount('new');
    setNewAccount({
      company_name: '',
      account_type: 'sms',
      url: '',
      username: '',
      password: '',
      status: 'active'
    });
  };

  // 계정 수정
  const handleEditAccount = (account) => {
    setEditingAccount(account.id);
    setNewAccount({
      company_name: account.company_name,
      account_type: account.account_type,
      url: account.site_url || account.url || '',
      username: account.username,
      password: account.password,
      status: account.status || 'active'
    });
  };

  // 계정 삭제
  const handleDeleteAccount = async (accountId) => {
    if (!window.confirm('정말로 이 계정을 삭제하시겠습니까?')) return;

    try {
      const response = await fetch(`${API_URL}/api/accounts/${accountId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await fetchAccounts();
      } else {
        alert('계정 삭제 실패');
      }
    } catch (error) {
      console.error('계정 삭제 오류:', error);
      alert('계정 삭제 중 오류가 발생했습니다.');
    }
  };

  // 계정 저장
  const handleSaveAccount = async () => {
    if (!newAccount.company_name || !newAccount.url || !newAccount.username || !newAccount.password) {
      alert('모든 필드를 입력해주세요.');
      return;
    }

    setSaving(true);
    try {
      const url = editingAccount === 'new' 
        ? `${API_URL}/api/accounts`
        : `${API_URL}/api/accounts/${editingAccount}`;
      
      const method = editingAccount === 'new' ? 'POST' : 'PUT';

      const response = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newAccount)
      });

      if (response.ok) {
        await fetchAccounts();
        setEditingAccount(null);
        setNewAccount({
          company_name: '',
          account_type: 'sms',
          url: '',
          username: '',
          password: '',
          status: 'active'
        });
      } else {
        const error = await response.json();
        alert(`저장 실패: ${error.error}`);
      }
    } catch (error) {
      console.error('계정 저장 오류:', error);
      alert('계정 저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  // 계정 취소
  const handleCancelEdit = () => {
    setEditingAccount(null);
    setNewAccount({
      company_name: '',
      account_type: 'sms',
      url: '',
      username: '',
      password: '',
      status: 'active'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-800 mx-auto"></div>
          <p className="mt-4 text-gray-600">계정 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              뒤로가기
            </button>
            <h1 className="text-2xl font-bold text-gray-900">계정 관리</h1>
          </div>
          <button
            onClick={handleAddAccount}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            계정 추가
          </button>
        </div>

        {/* 계정 목록 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">등록된 계정 목록</h2>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">보기 방식:</label>
                <select
                  value={viewType}
                  onChange={(e) => setViewType(e.target.value)}
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="project">프로젝트 별</option>
                  <option value="llm">LLM 계정 별</option>
                </select>
              </div>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            {viewType === 'project' ? (
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      회사명
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      계정 타입
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      URL
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      비밀번호
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      상태
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      작업
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(groupAccountsByCompany(accounts)).map(([companyName, companyAccounts]) => (
                    companyAccounts.map((account, index) => (
                      <tr key={account.id} className={`hover:bg-gray-50 ${index === 0 ? 'border-t-2 border-gray-300' : ''}`}>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 ${index === 0 ? 'bg-gray-50' : ''}`}>
                          {index === 0 ? companyName : ''}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            account.account_type === 'sms' 
                              ? 'bg-blue-100 text-blue-800' 
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {account.account_type === 'sms' ? 'SMS' : 'CALL'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="max-w-xs truncate" title={account.site_url || account.url}>
                            {account.site_url || account.url}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {account.username}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex items-center gap-2">
                            <span>
                              {showPasswords[account.id] ? account.password : '••••••••'}
                            </span>
                            <button
                              onClick={() => togglePasswordVisibility(account.id)}
                              className="text-gray-400 hover:text-gray-600"
                            >
                              {showPasswords[account.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            account.status === 'active' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {account.status === 'active' ? '활성' : '비활성'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleEditAccount(account)}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              수정
                            </button>
                            <button
                              onClick={() => handleDeleteAccount(account.id)}
                              className="text-red-600 hover:text-red-800"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-gray-500">
                <p>LLM 계정 목록이 여기에 표시됩니다.</p>
                <p className="text-sm mt-2">현재 LLM 계정이 등록되어 있지 않습니다.</p>
              </div>
            )}
          </div>
        </div>

        {/* 계정 추가/수정 모달 */}
        {editingAccount && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                {editingAccount === 'new' ? '새 계정 추가' : '계정 수정'}
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    회사명 *
                  </label>
                  <select
                    value={newAccount.company_name}
                    onChange={(e) => setNewAccount(prev => ({ ...prev, company_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">회사명을 선택하세요</option>
                    <option value="앤하우스">앤하우스</option>
                    <option value="디싸이더스/애드프로젝트">디싸이더스/애드프로젝트</option>
                    <option value="매스프레소(콴다)">매스프레소(콴다)</option>
                    <option value="SK일렉링크">SK일렉링크</option>
                    <option value="코오롱Fnc">코오롱Fnc</option>
                    <option value="W컨셉">W컨셉</option>
                    <option value="메디빌더">메디빌더</option>
                    <option value="구쁘">구쁘</option>
                    <option value="볼드워크">볼드워크</option>
                    <option value="코오롱">코오롱</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    계정 타입 *
                  </label>
                  <select
                    value={newAccount.account_type}
                    onChange={(e) => setNewAccount(prev => ({ ...prev, account_type: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="sms">SMS</option>
                    <option value="call">CALL</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    URL *
                  </label>
                  <input
                    type="url"
                    value={newAccount.url}
                    onChange={(e) => setNewAccount(prev => ({ ...prev, url: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="https://example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ID *
                  </label>
                  <input
                    type="text"
                    value={newAccount.username}
                    onChange={(e) => setNewAccount(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="ID를 입력하세요"
                  />
                </div>

                                 <div>
                   <label className="block text-sm font-medium text-gray-700 mb-1">
                     비밀번호 *
                   </label>
                   <input
                     type="password"
                     value={newAccount.password}
                     onChange={(e) => setNewAccount(prev => ({ ...prev, password: e.target.value }))}
                     className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                     placeholder="비밀번호를 입력하세요"
                   />
                 </div>

                 <div>
                   <label className="block text-sm font-medium text-gray-700 mb-1">
                     상태
                   </label>
                   <select
                     value={newAccount.status}
                     onChange={(e) => setNewAccount(prev => ({ ...prev, status: e.target.value }))}
                     className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                   >
                     <option value="active">활성</option>
                     <option value="inactive">비활성</option>
                   </select>
                 </div>


               </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={handleCancelEdit}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                >
                  취소
                </button>
                <button
                  onClick={handleSaveAccount}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {saving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      저장 중...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      저장
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountManager;
