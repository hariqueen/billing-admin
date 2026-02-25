import React, { useState } from 'react';
import { Menu, X, FileText, Receipt, CreditCard, Settings, User, LogOut } from 'lucide-react';
import BillingAutomationAdmin from './components/BillingAutomationAdmin';
import TaxInvoicePage from './components/TaxInvoicePage';
import AutoExpensePage from './components/AutoExpensePage';
import AccountManager from './components/AccountManager';
import LoginForm from './components/LoginForm';
import UserProfileManager from './components/UserProfileManager';

function App() {
  const [user, setUser] = useState(() => {
    // localStorage에서 사용자 정보 불러오기
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [currentPage, setCurrentPage] = useState('billing'); // 'billing', 'tax-invoice', 'auto-expense', 'profile'
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showAccountManager, setShowAccountManager] = useState(false);

  const handleLogin = (userData) => {
    // 로그인 시 localStorage에 사용자 정보 저장
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleUserUpdated = (updatedUser) => {
    localStorage.setItem('user', JSON.stringify(updatedUser));
    setUser(updatedUser);
  };

  const handleLogout = () => {
    // 로그아웃 시 localStorage에서 사용자 정보 제거
    localStorage.removeItem('user');
    setUser(null);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
    setShowAccountManager(false);
    setSidebarOpen(false);
  };

  const handleBackToMain = () => {
    setCurrentPage('billing');
    setShowAccountManager(false);
  };

  const renderCurrentPage = () => {
    if (showAccountManager) {
      return <AccountManager onBack={handleBackToMain} />;
    }

    switch (currentPage) {
      case 'billing':
        return (
          <BillingAutomationAdmin 
            user={user} 
            onLogout={handleLogout}
            onShowAccountManager={() => setShowAccountManager(true)}
          />
        );
      case 'tax-invoice':
        return <TaxInvoicePage onBack={() => setCurrentPage('billing')} user={user} />;
      case 'auto-expense':
        return <AutoExpensePage onBack={() => setCurrentPage('billing')} user={user} />;
      case 'profile':
        return (
          <UserProfileManager
            user={user}
            onBack={() => setCurrentPage('billing')}
            onUserUpdated={handleUserUpdated}
          />
        );
      default:
        return (
          <BillingAutomationAdmin 
            user={user} 
            onLogout={handleLogout}
            onShowAccountManager={() => setShowAccountManager(true)}
          />
        );
    }
  };

  if (!user) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <div className="App flex h-screen bg-gray-100">
      {/* 사이드바 오버레이 (모바일에서만) */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 데스크톱 사이드바 */}
      <div className="w-64 bg-white shadow-lg flex-shrink-0 lg:block hidden">
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
          <h1 className="text-lg font-semibold text-gray-900">관리자 시스템</h1>
        </div>

        <nav className="mt-4 px-4">
          <div className="space-y-2">
            <button
              onClick={() => handlePageChange('billing')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'billing' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <FileText className="w-5 h-5" />
              청구서 발행
            </button>
            
            <button
              onClick={() => handlePageChange('tax-invoice')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'tax-invoice' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Receipt className="w-5 h-5" />
              세금계산서 발행
            </button>
            
            <button
              onClick={() => handlePageChange('auto-expense')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'auto-expense' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <CreditCard className="w-5 h-5" />
              Auto 지출결의서
            </button>
          </div>

          <div className="mt-8 pt-4 border-t border-gray-200">
            <button
              onClick={() => {
                setShowAccountManager(true);
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                showAccountManager 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Settings className="w-5 h-5" />
              계정 관리
            </button>
            
            <button
              onClick={() => handlePageChange('profile')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'profile'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <User className="w-5 h-5" />
              내 계정
            </button>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <LogOut className="w-5 h-5" />
              로그아웃
            </button>
          </div>
        </nav>
      </div>

      {/* 모바일 사이드바 */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:hidden ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
          <h1 className="text-lg font-semibold text-gray-900">관리자 시스템</h1>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="mt-4 px-4">
          <div className="space-y-2">
            <button
              onClick={() => handlePageChange('billing')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'billing' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <FileText className="w-5 h-5" />
              청구서 발행
            </button>
            
            <button
              onClick={() => handlePageChange('tax-invoice')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'tax-invoice' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Receipt className="w-5 h-5" />
              세금계산서 발행
            </button>
            
            <button
              onClick={() => handlePageChange('auto-expense')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'auto-expense' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <CreditCard className="w-5 h-5" />
              Auto 지출결의서
            </button>
          </div>

          <div className="mt-8 pt-4 border-t border-gray-200">
            <button
              onClick={() => {
                setShowAccountManager(true);
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                showAccountManager 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Settings className="w-5 h-5" />
              계정 관리
            </button>
            
            <button
              onClick={() => handlePageChange('profile')}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'profile'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <User className="w-5 h-5" />
              내 계정
            </button>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <LogOut className="w-5 h-5" />
              로그아웃
            </button>
          </div>
        </nav>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 상단 헤더 */}
        <header className="bg-white shadow-sm border-b border-gray-200 lg:hidden">
          <div className="flex items-center justify-between h-16 px-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-md text-gray-400 hover:text-gray-600"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900">관리자 시스템</h1>
            <div className="w-10"></div> {/* 균형을 위한 빈 공간 */}
          </div>
        </header>

        {/* 페이지 콘텐츠 */}
        <main className="flex-1 overflow-y-auto">
          {renderCurrentPage()}
        </main>
      </div>
    </div>
  );
}

export default App;