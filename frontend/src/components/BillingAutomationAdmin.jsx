import React, { useState } from 'react';
import { Download, Upload, Play, Loader2 } from 'lucide-react';

const BillingAutomationAdmin = () => {
  const [dateRange, setDateRange] = useState({
    startDate: '2025-05-01',
    endDate: '2025-05-31'
  });

  const [companies, setCompanies] = useState([
    {
      name: '앤하우스',
      type: 'sms_call',
      collecting: false,
      collectedFiles: [],
      uploadedFile: null,
      processing: false,
      processedFile: null
    },
    {
      name: '디싸이더스/애드프로젝트',
      type: 'sms',
      collecting: false,
      collectedFiles: [],
      uploadedFile: null,
      processing: false,
      processedFile: null
    },
    {
      name: '매스프레소(콴다)',
      type: 'sms',
      collecting: false,
      collectedFiles: [],
      uploadedFile: null,
      processing: false,
      processedFile: null
    }
  ]);

  const handleDateChange = (field, value) => {
    setDateRange(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCollectData = async (companyName) => {
    setCompanies(prev => prev.map(company => 
      company.name === companyName 
        ? { ...company, collecting: true }
        : company
    ));

    try {
      // Python 백엔드 API 호출
      const response = await fetch('http://localhost:5001/api/collect-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: companyName,
          start_date: dateRange.startDate,
          end_date: dateRange.endDate
        })
      });

      const result = await response.json();
      
      if (response.ok) {
        // 작업 상태 폴링
        const taskId = result.task_id;
        pollTaskStatus(taskId, companyName);
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('데이터 수집 실패:', error);
      setCompanies(prev => prev.map(company => 
        company.name === companyName 
          ? { ...company, collecting: false }
          : company
      ));
    }
  };

  const pollTaskStatus = async (taskId, companyName) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`http://localhost:5001/api/task-status/${taskId}`);
        const status = await response.json();

        if (status.status === 'completed') {
          setCompanies(prev => prev.map(company => 
            company.name === companyName 
              ? { ...company, collecting: false, collectedFiles: status.files }
              : company
          ));
        } else if (status.status === 'failed') {
          console.error('작업 실패:', status.error);
          setCompanies(prev => prev.map(company => 
            company.name === companyName 
              ? { ...company, collecting: false }
              : company
          ));
        } else {
          // 아직 진행 중이면 3초 후 다시 확인
          setTimeout(checkStatus, 3000);
        }
      } catch (error) {
        console.error('상태 확인 실패:', error);
        setCompanies(prev => prev.map(company => 
          company.name === companyName 
            ? { ...company, collecting: false }
            : company
        ));
      }
    };

    checkStatus();
  };

  const handleFileUpload = (companyName, event) => {
    const file = event.target.files[0];
    if (file) {
      setCompanies(prev => prev.map(company => 
        company.name === companyName 
          ? { ...company, uploadedFile: file.name }
          : company
      ));
    }
  };

  const handleProcess = async (companyName) => {
    setCompanies(prev => prev.map(company => 
      company.name === companyName 
        ? { ...company, processing: true }
          : company
    ));

    // 전처리 시뮬레이션
    await new Promise(resolve => setTimeout(resolve, 2000));

    setCompanies(prev => prev.map(company => 
      company.name === companyName 
        ? { 
            ...company, 
            processing: false, 
            processedFile: `${companyName}_견적서_${dateRange.startDate}_${dateRange.endDate}.xlsx`
          }
        : company
    ));
  };

  const handleDownload = async (filename) => {
    try {
      const response = await fetch(`http://localhost:5001/api/download/${filename}`, {
        method: 'GET',
      });
  
      if (response.ok) {
        // Blob으로 응답 받기
        const blob = await response.blob();
        
        // 다운로드 링크 생성
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        
        // 다운로드 실행
        document.body.appendChild(link);
        link.click();
        
        // 정리
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        console.log(`✅ ${filename} 다운로드 완료`);
      } else {
        const error = await response.json();
        alert(`다운로드 실패: ${error.error}`);
      }
    } catch (error) {
      console.error('다운로드 오류:', error);
      alert(`다운로드 중 오류가 발생했습니다: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">청구자동화 어드민</h1>
          <p className="text-gray-600">서비스S본부 - 데이터 수집 및 전처리 시스템</p>
        </div>

        {/* 날짜 선택 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">조회 기간:</label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={dateRange.startDate}
                onChange={(e) => handleDateChange('startDate', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span className="text-gray-500">~</span>
              <input
                type="date"
                value={dateRange.endDate}
                onChange={(e) => handleDateChange('endDate', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* 컬럼 헤더 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-4">
          <div className="grid grid-cols-12 gap-4 text-sm font-medium text-gray-700">
            <div className="col-span-3">
              <div className="flex items-center gap-4">
                <span>ICS</span>
                <span>수집된 파일</span>
              </div>
            </div>
            <div className="col-span-1 border-l border-gray-200 pl-4"></div>
            <div className="col-span-8">
              <div className="flex items-center gap-8">
                <span>업로드</span>
                <span>전처리</span>
                <span>견적서</span>
              </div>
            </div>
          </div>
        </div>

        {/* 고객사 목록 */}
        <div className="space-y-3">
          {companies.map((company) => (
            <div key={company.name} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="grid grid-cols-12 gap-4 items-center">
                {/* ICS 및 수집된 파일 영역 */}
                <div className="col-span-3">
                  <div className="flex items-center gap-4">
                    {/* 회사명 버튼 */}
                    <button
                      onClick={() => handleCollectData(company.name)}
                      disabled={company.collecting}
                      className="px-4 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium min-w-[140px]"
                    >
                      {company.collecting ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          수집중
                        </div>
                      ) : (
                        company.name
                      )}
                    </button>

                    {/* 수집된 파일 */}
                    <div className="flex flex-col gap-1">
                      {company.collectedFiles.length > 0 ? (
                        company.collectedFiles.map((file, index) => (
                          <button
                            key={index}
                            onClick={() => handleDownload(file)}
                            className="text-blue-600 hover:text-blue-800 text-sm underline text-left"
                          >
                            {file}
                          </button>
                        ))
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 구분선 */}
                <div className="col-span-1 border-l border-gray-200 h-12"></div>

                {/* 업로드, 전처리, 견적서 영역 */}
                <div className="col-span-8">
                  <div className="flex items-center gap-8">
                    {/* 업로드 */}
                    <div className="flex items-center gap-2">
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          className="hidden"
                          accept=".xlsx,.xls"
                          onChange={(e) => handleFileUpload(company.name, e)}
                        />
                        <div className="w-10 h-10 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center hover:border-gray-400 transition-colors">
                          <Upload className="w-5 h-5 text-gray-400" />
                        </div>
                      </label>
                      {company.uploadedFile && (
                        <span className="text-sm text-gray-600 max-w-[120px] truncate">
                          {company.uploadedFile}
                        </span>
                      )}
                    </div>

                    {/* 전처리 실행 버튼 */}
                    <button
                      onClick={() => handleProcess(company.name)}
                      disabled={!company.uploadedFile || company.processing}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium flex items-center gap-2"
                    >
                      {company.processing ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          처리중
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          실행
                        </>
                      )}
                    </button>

                    {/* 견적서 파일 */}
                    <div className="flex-1">
                      {company.processedFile ? (
                        <button
                          onClick={() => handleDownload(company.processedFile)}
                          className="text-green-600 hover:text-green-800 text-sm underline"
                        >
                          {company.processedFile}
                        </button>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 하단 상태 정보 */}
        <div className="mt-8 p-4 bg-gray-100 rounded-lg">
          <div className="text-sm text-gray-600">
            <p>• 조회 기간: {dateRange.startDate} ~ {dateRange.endDate}</p>
            <p>• 수집 완료: {companies.filter(c => c.collectedFiles.length > 0).length}/{companies.length}개 고객사</p>
            <p>• 전처리 완료: {companies.filter(c => c.processedFile).length}/{companies.length}개 고객사</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BillingAutomationAdmin;