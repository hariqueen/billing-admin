import React, { useState } from 'react';
import { ArrowLeft, Upload, FileText, Play, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

// API URL을 환경에 따라 자동으로 선택 (BillingAutomationAdmin과 동일)
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5001'
  : `http://${window.location.hostname}:5001`;

// 한 달 전 1일부터 말일까지 날짜 계산 (청구서 발행과 동일한 로직)
const getPreviousMonthRange = () => {
  const today = new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth(); // 0-based (8월 = 7)
  
  // 한 달 전 계산
  let prevYear = currentYear;
  let prevMonth = currentMonth - 1;
  
  if (prevMonth < 0) {
    prevMonth = 11;
    prevYear = currentYear - 1;
  }
  
  // 한 달 전 1일 (로컬 시간대로 계산)
  const startDateStr = `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-01`;
  
  // 한 달 전 말일 (다음 달 0일 = 이번 달 마지막 날)
  const endDate = new Date(prevYear, prevMonth + 1, 0);
  const endDateStr = `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`;
  
  return {
    startDate: startDateStr,
    endDate: endDateStr
  };
};

const AutoExpensePage = ({ onBack, user }) => {
  const [dateRange, setDateRange] = useState(getPreviousMonthRange());
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState('해외결제 법인카드');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState('');
  const [results, setResults] = useState(null);

  const handleDateChange = (field, value) => {
    setDateRange(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFileSelect = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      const validTypes = [
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv'
      ];
      
      if (validTypes.includes(selectedFile.type) || selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
      } else {
        alert('Excel 파일(.xlsx, .xls) 또는 CSV 파일만 업로드 가능합니다.');
      }
    }
  };

  const validateInputs = () => {
    if (!file) {
      alert('파일을 선택해주세요.');
      return false;
    }
    
    if (!dateRange.startDate || !dateRange.endDate) {
      alert('날짜를 입력해주세요.');
      return false;
    }
    
    if (!user?.employeeId || !user?.password) {
      alert('로그인 정보가 없습니다. 다시 로그인해주세요.');
      return false;
    }
    
    return true;
  };

  const handleStartAutomation = async () => {
    if (!validateInputs()) return;
    
    setIsProcessing(true);
    setProgress('파일을 업로드하는 중...');
    setResults(null);
    
    try {
      // 날짜를 YYYYMMDD 형식으로 변환
      const formatDateToYYYYMMDD = (dateStr) => {
        return dateStr.replace(/-/g, '');
      };

      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', category);
      formData.append('start_date', formatDateToYYYYMMDD(dateRange.startDate));
      formData.append('end_date', formatDateToYYYYMMDD(dateRange.endDate));
      // 로그인 정보 사용
      formData.append('user_id', user.employeeId);
      formData.append('password', user.password);
      
      console.log('🚀 지출결의서 자동화 요청 시작');
      console.log('   API URL:', `${API_URL}/api/expense-automation`);
      console.log('   파일명:', file.name);
      console.log('   카테고리:', category);
      console.log('   날짜:', formatDateToYYYYMMDD(dateRange.startDate), '~', formatDateToYYYYMMDD(dateRange.endDate));
      console.log('   사용자 ID:', user.employeeId);
      
      const response = await fetch(`${API_URL}/api/expense-automation`, {
        method: 'POST',
        body: formData
      });
      
      console.log('📥 서버 응답 수신:', response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ 서버 오류 응답:', errorText);
        throw new Error(`서버 오류: ${response.status} - ${errorText.substring(0, 200)}`);
      }
      
      const result = await response.json();
      console.log('✅ 서버 응답 데이터:', result);
      
      if (result.success) {
        setResults({
          success: true,
          message: result.message,
          processed_count: result.processed_count,
          total_count: result.total_count
        });
        setProgress('작업이 완료되었습니다!');
      } else {
        throw new Error(result.error || '알 수 없는 오류가 발생했습니다.');
      }
      
    } catch (error) {
      console.error('❌ 자동화 실행 오류:', error);
      console.error('   오류 상세:', error.stack);
      setResults({
        success: false,
        message: error.message
      });
      setProgress('오류가 발생했습니다.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* 헤더 */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            뒤로가기
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Auto 지출결의서</h1>
        </div>

        <div className="space-y-6">
          {/* 날짜 설정 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              1. 조회 기간 설정
            </h3>
            <div className="flex items-center gap-3">
              <input
                type="date"
                value={dateRange.startDate}
                onChange={(e) => handleDateChange('startDate', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span className="text-gray-500 mx-2">~</span>
              <input
                type="date"
                value={dateRange.endDate}
                onChange={(e) => handleDateChange('endDate', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* 로그인 정보 표시 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-5 h-5 text-blue-600" />
              <h3 className="font-medium text-blue-900">로그인 정보</h3>
            </div>
            <p className="text-blue-700">
              현재 로그인된 계정: <span className="font-medium">{user?.name} ({user?.employeeId})</span>
            </p>
            <p className="text-sm text-blue-600 mt-1">
              그룹웨어 자동화는 시스템 계정(admin)으로 실행됩니다.
            </p>
          </div>

          {/* 파일 업로드 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5" />
              2. 파일 업로드
            </h3>
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <input
                type="file"
                id="file-upload"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileSelect}
                className="hidden"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center gap-2"
              >
                <FileText className="w-12 h-12 text-gray-400" />
                <span className="text-lg text-gray-600">
                  {file ? file.name : 'CSV/Excel 파일을 선택하세요'}
                </span>
                <span className="text-sm text-gray-500">
                  또는 파일을 여기로 드래그하세요
                </span>
              </label>
            </div>
            
            {file && (
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-green-700 text-sm">
                  ✅ 파일 선택됨: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                </p>
              </div>
            )}
          </div>

          {/* 카테고리 설정 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              3. 카테고리 설정
            </h3>
            
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="category"
                  value="해외결제 법인카드"
                  checked={category === '해외결제 법인카드'}
                  onChange={(e) => setCategory(e.target.value)}
                  className="mr-2"
                />
                해외결제 법인카드
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="category"
                  value="그 외"
                  checked={category === '그 외'}
                  onChange={(e) => setCategory(e.target.value)}
                  className="mr-2"
                />
                그 외
              </label>
            </div>
          </div>



          {/* 실행 버튼 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              4. 자동화 실행
            </h3>
            <button
              onClick={handleStartAutomation}
              disabled={isProcessing}
              className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-md text-white font-medium transition-colors ${
                isProcessing
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  처리 중...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  지출결의서 자동입력 시작
                </>
              )}
            </button>
          </div>

          {/* 진행상황 */}
          {(progress || results) && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                진행상황
              </h3>
              
              {progress && (
                <div className="mb-4">
                  <p className="text-gray-700">{progress}</p>
                  {isProcessing && (
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{width: '50%'}}></div>
                    </div>
                  )}
                </div>
              )}
              
              {results && (
                <div className={`p-4 rounded-md ${
                  results.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    {results.success ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    )}
                    <h4 className={`font-medium ${
                      results.success ? 'text-green-900' : 'text-red-900'
                    }`}>
                      {results.success ? '작업 완료' : '오류 발생'}
                    </h4>
                  </div>
                  
                  <p className={`${
                    results.success ? 'text-green-700' : 'text-red-700'
                  }`}>
                    {results.message}
                  </p>
                  
                  {results.success && results.processed_count !== undefined && (
                    <p className="text-green-600 text-sm mt-2">
                      처리된 레코드: {results.processed_count}/{results.total_count}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 하단 상태 정보 */}
          <div className="bg-gray-100 rounded-lg p-4">
            <div className="text-sm text-gray-600">
              <p>• 조회 기간: {dateRange.startDate} ~ {dateRange.endDate}</p>
              <p>• 그룹웨어 계정: {user?.name} ({user?.employeeId})</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AutoExpensePage;