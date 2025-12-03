import React, { useState, useEffect } from 'react';
import { Download, Upload, Play, Loader2, RotateCcw } from 'lucide-react';

// API URL을 환경에 따라 자동으로 선택
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5001'
  : `http://${window.location.hostname}:5001`;

// 한 달 전 1일부터 말일까지 날짜 계산 함수
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

const BillingAutomationAdmin = ({ user, onLogout, onShowAccountManager }) => {
  const [dateRange, setDateRange] = useState(getPreviousMonthRange());

  const [filePopup, setFilePopup] = useState({
    isOpen: false,
    companyName: '',
    files: []
  });

  const [licensePopup, setLicensePopup] = useState({
    isOpen: false,
    companyName: '',
    licenseCount: 40
  });



  const [companies, setCompanies] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  // 고객사 목록 가져오기
  // 통신비 정보 가져오기
  const fetchBillAmounts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bill-amounts`);
      const data = await response.json();
      
      // 회사 정보 업데이트
      setCompanies(prev => prev.map(company => ({
        ...company,
        billAmount: data[company.name]?.amount,
        billUpdateDate: data[company.name]?.update_date,
        billImagePath: data[company.name]?.image_path,
        billPdfFile: data[company.name]?.pdf_file
      })));
    } catch (error) {
      console.error('통신비 정보 가져오기 실패:', error);
    }
  };

  // 통신비 업로드 처리
  const handleBillUpload = async (event) => {
    const files = event.target.files;
    if (files.length === 0) return;

    setIsUploading(true);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files[]', files[i]);
    }

    try {
      const response = await fetch(`${API_URL}/api/upload-bills`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      
      if (response.ok) {
        console.log('통신비 처리 완료:', result);
        // 통신비 정보 새로고침
        await fetchBillAmounts();
      } else {
        alert(`통신비 처리 실패: ${result.error}`);
      }
    } catch (error) {
      console.error('통신비 업로드 실패:', error);
      alert('통신비 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsUploading(false);
    }

    // 파일 선택 초기화
    event.target.value = '';
  };


  // 저장된 파일 목록 로드
  const loadProcessedFiles = async () => {
    try {
      const response = await fetch(`${API_URL}/api/get-processed-files`);
      const data = await response.json();
      
      if (response.ok) {
        // 저장된 결과를 회사별로 적용
        setCompanies(prev => prev.map(company => ({
          ...company,
          processedFiles: data.processed_files?.[company.name]?.processed_files || [],
          uploadedFiles: data.uploaded_files?.[company.name] || [],
          collectedFiles: data.collected_files?.[company.name] || []
        })));
      }
    } catch (error) {
      console.error('파일 목록 로드 실패:', error);
    }
  };

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        console.log('🔍 고객사 목록 가져오기 시작...');
        console.log('API URL:', `${API_URL}/api/companies`);
        const response = await fetch(`${API_URL}/api/companies`);
        console.log('API 응답 상태:', response.status, response.statusText);
        const data = await response.json();
        console.log('받은 데이터:', data);
        
        // 고객사별 설정
        const companyConfigs = {
          '앤하우스': {
            type: 'sms_call',
            requiredFileCount: 2,
            fileLabels: ['SMS 데이터', 'CALL 데이터']
          },
          '디싸이더스/애드프로젝트': {
            type: 'sms',
            requiredFileCount: 5,
            fileLabels: ['SMS 데이터', 'CHAT 데이터', '추가 파일 1', '추가 파일 2', '추가 파일 3']
          },
          '매스프레소(콴다)': {
            type: 'sms',
            requiredFileCount: 1,
            fileLabels: ['SMS 데이터']
          },
          '코오롱Fnc': {
            type: 'manual',
            requiredFileCount: 2,
            fileLabels: ['데이터 파일 1', '데이터 파일 2']
          },
          'SK일렉링크': {
            type: 'manual',
            requiredFileCount: 1,
            fileLabels: ['데이터 파일']
          },
          'W컨셉': {
            type: 'manual',
            requiredFileCount: 1,
            fileLabels: ['데이터 파일']
          },
          '메디빌더': {
            type: 'manual',
            requiredFileCount: 2,
            fileLabels: ['데이터 파일 1', '데이터 파일 2']
          },
          '구쁘': {
            type: 'sms',
            requiredFileCount: 1,
            fileLabels: ['SMS 데이터']
          }
        };

        // 고객사 목록 설정
        const formattedCompanies = data.companies.map(name => ({
          name,
          ...companyConfigs[name],
          collecting: false,
          collectedFiles: [],
          uploadedFiles: [],
          processing: false,
          processedFiles: []
        }));

        setCompanies(formattedCompanies);
        
        // 통신비 정보도 함께 가져오기
        fetchBillAmounts();
        
        // 저장된 청구서 결과 로드
        setTimeout(() => loadProcessedFiles(), 500); // 회사 설정 후 약간의 딜레이
      } catch (error) {
        console.error('고객사 목록 가져오기 실패:', error);
      }
    };

    fetchCompanies();
  }, []);

  const handleDateChange = (field, value) => {
    setDateRange(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleReset = async () => {
    if (!window.confirm('모든 데이터를 초기화하시겠습니까?\n(고지서 금액, 업로드된 파일, 청구서 파일이 모두 삭제됩니다)')) {
      return;
    }

    try {
      const resetResponse = await fetch(`${API_URL}/api/reset`, {
        method: 'POST'
      });
      const resetResult = await resetResponse.json();
      
      if (!resetResponse.ok) {
        alert(resetResult.error || '초기화 실패');
        return;
      }

      setDateRange(getPreviousMonthRange());
      setCompanies(prev => prev.map(company => ({
        ...company,
        uploadedFiles: [],
        collectedFiles: [],
        processedFiles: [],
        collecting: false,
        processing: false,
        billAmount: undefined,
        billUpdateDate: undefined,
        billImagePath: undefined,
        billPdfFile: undefined
      })));

      alert('초기화가 완료되었습니다.');
    } catch (error) {
      console.error('초기화 실패:', error);
      alert('초기화 중 오류가 발생했습니다.');
    }
  };

  const handleCollectData = async (companyName) => {
    setCompanies(prev => prev.map(company => 
      company.name === companyName 
        ? { ...company, collecting: true }
        : company
    ));

    try {
      // Python 백엔드 API 호출 (날짜가 선택되지 않은 경우 빈 값으로 전송하여 백엔드에서 기본값 사용)
      const requestBody = {
        company_name: companyName
      };
      
      // 날짜가 선택된 경우에만 전송
      if (dateRange.startDate && dateRange.endDate) {
        requestBody.start_date = dateRange.startDate;
        requestBody.end_date = dateRange.endDate;
      }
      
      const response = await fetch(`${API_URL}/api/collect-data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
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
        const response = await fetch(`${API_URL}/api/task-status/${taskId}`);
        const status = await response.json();

        if (status.status === 'completed') {
          console.log(`수집 완료 - ${companyName}:`, status);
          console.log(`수집된 파일 목록:`, status.files);
          console.log(`파일 타입:`, typeof status.files, Array.isArray(status.files));
          console.log(`파일 개수:`, status.files ? status.files.length : 0);
          
          const filesArray = Array.isArray(status.files) ? status.files : (status.files || []);
          
          setCompanies(prev => prev.map(company => 
            company.name === companyName 
              ? { ...company, collecting: false, collectedFiles: filesArray }
              : company
          ));
          
          // 수집된 파일 목록 저장
          if (filesArray && filesArray.length > 0) {
            console.log(`수집된 파일 목록 저장 시작: ${companyName}`, filesArray);
            try {
              const saveResponse = await fetch(`${API_URL}/api/save-collected-files`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  company_name: companyName,
                  collected_files: filesArray
                })
              });
              const saveResult = await saveResponse.json();
              console.log(`수집된 파일 목록 저장 결과:`, saveResult);
            } catch (error) {
              console.error('수집된 파일 목록 저장 실패:', error);
            }
          } else {
            console.warn(`수집된 파일이 없어 저장하지 않음: ${companyName}`, filesArray);
          }
          
          // 앤하우스, 디싸이더스/애드프로젝트, 매스프레소(콴다), 구쁘인 경우 수집된 파일들을 자동으로 업로드
          if ((companyName === '앤하우스' || companyName === '디싸이더스/애드프로젝트' || companyName === '매스프레소(콴다)' || companyName === '구쁘') && filesArray && filesArray.length > 0) {
            console.log(`${companyName} 자동 업로드 조건 만족 - 파일 수: ${filesArray.length}`);
            autoUploadCollectedFiles(companyName, filesArray);
          } else {
            console.log(`${companyName} 자동 업로드 조건 불만족:`, {
              isTargetCompany: (companyName === '앤하우스' || companyName === '디싸이더스/애드프로젝트' || companyName === '매스프레소(콴다)' || companyName === '구쁘'),
              hasFiles: filesArray && filesArray.length > 0,
              filesLength: filesArray ? filesArray.length : 0
            });
          }
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

  const autoUploadCollectedFiles = async (companyName, collectedFiles) => {
    try {
      const company = companies.find(c => c.name === companyName);
      
      // 중복 업로드 방지
      const existingUploads = company.uploadedFiles.filter(file => file).length;
      if (existingUploads > 0) {
        console.log(`${companyName}는 이미 ${existingUploads}개 파일이 업로드되어 있어 자동 업로드를 건너뜁니다.`);
        return;
      }
      
      // SMS 파일은 앞쪽에, CALL/CHAT 파일은 마지막에 배치
      const smsFiles = collectedFiles.filter(f => f.includes('발송이력'));
      const callFiles = collectedFiles.filter(f => f.includes('통화내역'));
      const chatFiles = collectedFiles.filter(f => f.includes('채팅'));
      const allFiles = [...smsFiles, ...callFiles, ...chatFiles];

      console.log(`${companyName} 자동 업로드 시작: ${allFiles.length}개 파일`);
      
      // 기존 업로드된 파일 초기화
      setCompanies(prev => prev.map(comp => 
        comp.name === companyName 
          ? { ...comp, uploadedFiles: [] }
          : comp
      ));

      // 순차적으로 파일 업로드
      for (let i = 0; i < allFiles.length; i++) {
        const filename = allFiles[i];
        let fileLabel = 'SMS 데이터';
        if (filename.includes('통화내역')) {
          fileLabel = 'CALL 데이터';
        } else if (filename.includes('채팅')) {
          fileLabel = 'CHAT 데이터';
        }
        
        try {
          const formData = new FormData();
          formData.append('company_name', companyName);
          formData.append('collected_filename', filename);
          formData.append('file_index', i.toString());
          formData.append('file_label', fileLabel);

          const response = await fetch(`${API_URL}/api/upload-file`, {
            method: 'POST',
            body: formData
          });

          const result = await response.json();
          
          if (response.ok) {
            console.log(`자동 업로드 완료: ${filename} -> ${result.filename}`);
            // 파일 업로드 후 상태 업데이트
            setCompanies(prev => {
              const updatedCompanies = prev.map(comp => 
                comp.name === companyName 
                  ? { ...comp, uploadedFiles: [...(comp.uploadedFiles || []), result.filename] }
                  : comp
              );
              
              // 업로드된 파일 목록 저장
              const updatedCompany = updatedCompanies.find(c => c.name === companyName);
              if (updatedCompany) {
                fetch(`${API_URL}/api/save-uploaded-files`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    company_name: companyName,
                    uploaded_files: updatedCompany.uploadedFiles
                  })
                }).catch(error => console.error('업로드된 파일 목록 저장 실패:', error));
              }
              
              return updatedCompanies;
            });
          } else {
            console.error(`자동 업로드 실패 (${filename}):`, result.error);
          }
        } catch (error) {
          console.error(`자동 업로드 오류 (${filename}):`, error);
        }
      }
      
      console.log('모든 파일 업로드 완료');
      
      // 모든 파일 업로드 완료 후 저장
      const finalCompany = companies.find(c => c.name === companyName);
      if (finalCompany) {
        try {
          await fetch(`${API_URL}/api/save-uploaded-files`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              company_name: companyName,
              uploaded_files: finalCompany.uploadedFiles || []
            })
          });
        } catch (error) {
          console.error('업로드된 파일 목록 저장 실패:', error);
        }
      }
      
    } catch (error) {
      console.error('자동 업로드 오류:', error);
    }
  };



  const showFilePopup = (companyName) => {
    const company = companies.find(c => c.name === companyName);
    setFilePopup({
      isOpen: true,
      companyName: companyName,
      files: company.uploadedFiles.map((file, index) => ({
        label: company.fileLabels[index],
        filename: file || null
      }))
    });
  };

  const closeFilePopup = () => {
    setFilePopup({ isOpen: false, companyName: '', files: [] });
  };

  const showLicensePopup = (companyName) => {
    setLicensePopup({
      isOpen: true,
      companyName: companyName,
      licenseCount: 40
    });
  };

  const closeLicensePopup = () => {
    setLicensePopup({ isOpen: false, companyName: '', licenseCount: 40 });
  };

  const handleLicenseConfirm = async () => {
    const { companyName, licenseCount } = licensePopup;
    closeLicensePopup();
    await handleProcess(companyName, licenseCount);
  };

  // W컨셉 전용 알림창 표시 (자동 사라짐)
  const showWConceptNotification = () => {
    // 알림 요소 생성
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: #10b981;
      color: white;
      padding: 20px 30px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 9999;
      font-size: 16px;
      font-weight: 500;
      text-align: center;
      max-width: 400px;
      animation: fadeInOut 3s ease-in-out;
    `;
    notification.textContent = 'W컨셉은 고객사의 요청으로 전 달 청구서로 발행됩니다.';

    // CSS 애니메이션 추가
    const style = document.createElement('style');
    style.textContent = `
      @keyframes fadeInOut {
        0% { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
        15% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        85% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        100% { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
      }
    `;
    document.head.appendChild(style);

    // DOM에 추가
    document.body.appendChild(notification);

    // 3초 후 자동 제거
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
      if (style.parentNode) {
        style.parentNode.removeChild(style);
      }
    },);
  };

  // 청구서 결과 초기화
  const clearProcessedFiles = async (companyName) => {
    try {
      const response = await fetch(`${API_URL}/api/clear-processed-files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ company_name: companyName })
      });
      
      if (response.ok) {
        // 프론트엔드 상태도 업데이트
        setCompanies(prev => prev.map(comp => 
          comp.name === companyName 
            ? { ...comp, processedFiles: [] }
            : comp
        ));
        console.log(`✅ ${companyName} 청구서 결과 초기화 완료`);
      }
    } catch (error) {
      console.error('청구서 결과 초기화 실패:', error);
    }
  };

  const handleMultipleFileUpload = async (companyName, event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    // 새 파일 업로드 시 청구서 결과 초기화
    await clearProcessedFiles(companyName);

    const company = companies.find(c => c.name === companyName);
    
    try {
      const uploadedFiles = [...company.uploadedFiles];
      let uploadIndex = 0;
      
      for (const file of files) {
        // 빈 슬롯 찾기
        while (uploadIndex < company.requiredFileCount && uploadedFiles[uploadIndex]) {
          uploadIndex++;
        }
        
        if (uploadIndex >= company.requiredFileCount) {
          alert(`${companyName}는 최대 ${company.requiredFileCount}개 파일만 업로드 가능합니다.`);
          break;
        }

        const fileLabel = company.fileLabels[uploadIndex];
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('company_name', companyName);
        formData.append('file_index', uploadIndex.toString());
        formData.append('file_label', fileLabel);

        const response = await fetch(`${API_URL}/api/upload-file`, {
          method: 'POST',
          body: formData
        });

        const result = await response.json();

        if (response.ok) {
          uploadedFiles[uploadIndex] = result.filename;
          console.log(`${fileLabel} 업로드 완료: ${result.filename}`);
        } else {
          console.error(`${fileLabel} 업로드 실패:`, result.error);
        }
        
        uploadIndex++;
      }
      
      // 상태 업데이트
      setCompanies(prev => prev.map(comp => 
        comp.name === companyName 
          ? { ...comp, uploadedFiles: uploadedFiles }
          : comp
      ));
      
      // 업로드된 파일 목록 저장
      try {
        await fetch(`${API_URL}/api/save-uploaded-files`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_name: companyName,
            uploaded_files: uploadedFiles
          })
        });
      } catch (error) {
        console.error('업로드된 파일 목록 저장 실패:', error);
      }
      
    } catch (error) {
      console.error('다중 파일 업로드 실패:', error);
      alert(`파일 업로드 실패: ${error.message}`);
    }
    
    // 파일 선택 초기화
    event.target.value = '';
  };

  const handleProcess = async (companyName, licenseCount = null) => {
    const company = companies.find(c => c.name === companyName);
    
    // SK일렉링크와 W컨셉은 고지서 업로드 여부만 확인
    if (companyName === 'SK일렉링크' || companyName === 'W컨셉') {
      if (!company.billAmount) {
        alert(`${companyName}는 고지서가 업로드되어야 전처리가 가능합니다.`);
        return;
      }
    } else {
      // 다른 회사들은 기존 로직 적용
      const uploadedCount = company.uploadedFiles.filter(file => file).length;
      
      // 디싸이더스는 최소 2개 이상, 다른 회사는 필수 개수 모두 필요
      const minRequiredFiles = companyName === '디싸이더스/애드프로젝트' ? 2 : company.requiredFileCount;
      
      if (uploadedCount < minRequiredFiles) {
        alert(`${companyName}는 최소 ${minRequiredFiles}개의 파일이 필요합니다. 현재 ${uploadedCount}개 업로드됨.`);
        return;
      }
    }

    setCompanies(prev => prev.map(comp => 
      comp.name === companyName 
        ? { ...comp, processing: true }
        : comp
    ));

    try {
      // 실제 전처리 API 호출
      const requestBody = {
        company_name: companyName,
        collection_date: dateRange.startDate  // YYYY-MM-DD 형식
      };

      // W컨셉인 경우 라이선스 수량 추가
      if (companyName === 'W컨셉' && licenseCount !== null) {
        requestBody.license_count = licenseCount;
      }

      const response = await fetch(`${API_URL}/api/process-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      const result = await response.json();
      
      if (response.ok) {
        console.log(`${companyName} 전처리 완료:`, result);
        
        setCompanies(prev => prev.map(comp => 
          comp.name === companyName 
            ? { ...comp, processing: false, processedFiles: result.processed_files || [] }
            : comp
        ));

        // W컨셉인 경우 특별 알림창 표시
        if (companyName === 'W컨셉') {
          showWConceptNotification();
        }
      } else {
        console.error(`${companyName} 전처리 실패:`, result.error);
        alert(`전처리 실패: ${result.error}`);
        
        setCompanies(prev => prev.map(comp => 
          comp.name === companyName 
            ? { ...comp, processing: false }
            : comp
        ));
      }
    } catch (error) {
      console.error(`${companyName} 전처리 오류:`, error);
      alert(`전처리 중 오류가 발생했습니다: ${error.message}`);
      
      setCompanies(prev => prev.map(comp => 
        comp.name === companyName 
          ? { ...comp, processing: false }
          : comp
      ));
    }
  };

  // 파일명을 일정 길이로 자르고 "..." 추가
  const truncateFilename = (filename, maxLength = 30) => {
    if (!filename || filename.length <= maxLength) return filename;
    return filename.substring(0, maxLength) + '...';
  };

  const handleDownload = async (filename) => {
    try {
      const response = await fetch(`${API_URL}/api/download/${filename}`, {
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
        
        console.log(`${filename} 다운로드 완료`);
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
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">청구자동화 어드민</h1>
            <p className="text-gray-600">서비스S본부 - 데이터 수집 및 전처리 시스템</p>
          </div>
          
          {/* 사용자 정보 */}
          {user && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">
                  {user.name} {user.position}
                </div>
                <div className="text-xs text-gray-500">
                  {user.employeeId}
                </div>
              </div>
              <button
                onClick={onLogout}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
              >
                로그아웃
              </button>
            </div>
          )}
        </div>

        {/* 날짜 선택 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">조회 기간:</label>
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
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-md transition-colors text-sm font-medium"
              title="모든 데이터 초기화 (고지서, 청구서, 업로드 파일)"
            >
              <RotateCcw className="w-4 h-4" />
              초기화
            </button>
          </div>
        </div>

        {/* 컬럼 헤더 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-4">
          <div className="grid grid-cols-12 gap-6 text-sm font-medium text-gray-700">
            {/* ISC/PJ명 헤더 */}
            <div className="col-span-2 text-center">
              <span>ISC/PJ명</span>
            </div>
            
            {/* 고지서 헤더 */}
            <div className="col-span-3 flex items-center justify-center gap-3">
              <span>고지서</span>
              {/* 고지서 일괄 업로드 (HTML/PDF 통합) */}
              <div className="relative">
                <label className={`cursor-pointer ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
                  <input
                    type="file"
                    className="hidden"
                    accept=".html,.pdf"
                    multiple
                    onChange={handleBillUpload}
                    disabled={isUploading}
                  />
                  <div className="w-8 h-8 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center hover:border-gray-400 transition-colors">
                    {isUploading ? (
                      <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                    ) : (
                      <Upload className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </label>
              </div>
            </div>
            
            {/* 구분선 */}
            <div className="col-span-1 flex justify-center">
              <div className="border-l border-gray-200 h-6"></div>
            </div>
            
            {/* 업로드 헤더 */}
            <div className="col-span-2 text-center">
              <span>업로드</span>
            </div>
            
            {/* 전처리 헤더 */}
            <div className="col-span-2 text-center">
              <span>전처리</span>
            </div>
            
            {/* 청구서 헤더 */}
            <div className="col-span-2 text-center">
              <span>청구서</span>
            </div>
          </div>
        </div>

        {/* 고객사 목록 */}
        <div className="space-y-3">
          {companies.map((company) => (
            <div key={company.name} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 overflow-hidden">
              <div className="grid grid-cols-12 gap-6 items-center" style={{ width: '100%', overflow: 'hidden' }}>
                {/* ISC/PJ명 영역 */}
                <div className="col-span-2 flex justify-center">
                  <button
                    onClick={() => company.type !== 'manual' && handleCollectData(company.name)}
                    disabled={company.collecting || company.type === 'manual'}
                    className="px-4 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium min-w-[140px]"
                  >
                    {company.collecting ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        수집중
                      </div>
                    ) : (
                      company.name === '디싸이더스/애드프로젝트' ? (
                        <div className="text-center">
                          <div>디싸이더스</div>
                          <div>애드프로젝트</div>
                        </div>
                      ) : (
                        company.name
                      )
                    )}
                  </button>
                </div>

                {/* 고지서 영역 */}
                <div className="col-span-3 flex flex-col justify-center items-center gap-1">
                  {company.billAmount ? (
                    <div className="flex flex-col items-center gap-1">
                      <span className="text-green-600 font-medium">
                        {company.billAmount}
                      </span>
                      <span className="text-gray-400 text-xs">
                        {company.billUpdateDate} 업데이트
                      </span>
                    </div>
                  ) : (
                    <span className="text-gray-400 text-sm">-</span>
                  )}
                </div>

                {/* 구분선 */}
                <div className="col-span-1 flex justify-center items-center">
                  <div className="border-l border-gray-200 h-full min-h-[80px]"></div>
                </div>

                {/* 업로드 영역 */}
                <div className="col-span-2 flex justify-center">
                  <div className="flex flex-col items-center gap-2">
                    {/* 업로드 박스 */}
                    <div className="relative">
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          className="hidden"
                          accept=".xlsx,.xls,.csv"
                          multiple
                          onChange={(e) => handleMultipleFileUpload(company.name, e)}
                        />
                        <div className="w-12 h-12 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center hover:border-gray-400 transition-colors">
                          <Upload className="w-6 h-6 text-gray-400" />
                        </div>
                      </label>
                      
                      {/* 업로드된 파일 개수 표시 */}
                      {company.uploadedFiles.filter(file => file).length > 0 && (
                        <div 
                          className="absolute -top-1 -right-1 bg-green-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center shadow-lg"
                          style={{ zIndex: 50 }}
                        >
                          {company.uploadedFiles.filter(file => file).length}
                        </div>
                      )}
                    </div>
                    
                    {/* 파일 목록 보기 버튼 */}
                    {company.uploadedFiles.filter(file => file).length > 0 && (
                      <button
                        onClick={() => showFilePopup(company.name)}
                        className="text-xs text-blue-600 hover:text-blue-800 underline"
                      >
                        파일 목록 보기
                      </button>
                    )}
                    
                    {/* 진행률 표시 */}
                    <div className="text-xs text-gray-500">
                      {company.uploadedFiles.filter(file => file).length}/{company.requiredFileCount} 완료
                    </div>
                  </div>
                </div>

                {/* 전처리 영역 */}
                <div className="col-span-2 flex justify-center">
                  <button
                    onClick={() => company.name === 'W컨셉' ? showLicensePopup(company.name) : handleProcess(company.name)}
                    disabled={
                      company.processing || (
                        company.name === 'SK일렉링크' || company.name === 'W컨셉'
                          ? !company.billAmount  // SK일렉링크와 W컨셉은 고지서 업로드 여부만 확인
                          : company.name === '디싸이더스/애드프로젝트' 
                            ? company.uploadedFiles.filter(file => file).length < 2 
                            : company.uploadedFiles.filter(file => file).length < company.requiredFileCount
                      )
                    }
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
                </div>

                {/* 청구서 영역 */}
                <div className="col-span-2" style={{ minWidth: 0, width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
                  {/* 청구내역서 파일들 */}
                  {company.processedFiles && company.processedFiles.length > 0 ? (
                    <div className="space-y-1">
                      {company.processedFiles.map((filename, index) => (
                        <button
                          key={index}
                          onClick={() => handleDownload(filename)}
                          className="text-green-600 hover:text-green-800 text-sm underline text-left"
                          title={filename}
                        >
                          {truncateFilename(filename)}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <span className="text-gray-400 text-sm">-</span>
                  )}
                  
                  {/* 통신비 PDF (HTML에서 생성) */}
                  {company.billImagePath && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <button
                        onClick={() => window.open(`${API_URL}/api/bill-image/${company.billImagePath.split('/').pop()}`, '_blank')}
                        className="text-blue-600 hover:text-blue-800 text-sm underline text-left"
                        title={company.billImagePath.split('/').pop()}
                      >
                        {truncateFilename(company.billImagePath.split('/').pop())}
                      </button>
                    </div>
                  )}
                  
                  {/* 고지서 PDF (직접 업로드) */}
                  {company.billPdfFile && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <button
                        onClick={() => window.open(`${API_URL}/api/bill-pdf/${company.billPdfFile}`, '_blank')}
                        className="text-blue-600 hover:text-blue-800 text-sm underline text-left"
                        title={company.billPdfFile}
                      >
                        {truncateFilename(company.billPdfFile)}
                      </button>
                    </div>
                  )}
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
            <p>• 업로드 완료: {companies.filter(c => {
              const uploadedCount = c.uploadedFiles.filter(file => file).length;
              const minRequired = c.name === '디싸이더스/애드프로젝트' ? 2 : c.requiredFileCount;
              return uploadedCount >= minRequired;
            }).length}/{companies.length}개 고객사</p>
            <p>• 전처리 완료: {companies.filter(c => c.processedFiles && c.processedFiles.length > 0).length}/{companies.length}개 고객사</p>
          </div>
        </div>

        {/* 파일 목록 팝업 */}
        {filePopup.isOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {filePopup.companyName} - 업로드된 파일
                </h3>
                <button
                  onClick={closeFilePopup}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-3">
                {filePopup.files.map((fileInfo, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-gray-700">
                        {fileInfo.label}
                      </span>
                      {fileInfo.filename ? (
                        <span className="text-xs text-green-600">
                          ✓ {fileInfo.filename}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">
                          업로드 대기중
                        </span>
                      )}
                    </div>
                    {fileInfo.filename && (
                      <button
                        onClick={() => handleDownload(fileInfo.filename)}
                        className="text-blue-600 hover:text-blue-800 text-xs"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              
              <div className="mt-4 text-center">
                <button
                  onClick={closeFilePopup}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 라이선스 수량 입력 팝업 */}
        {licensePopup.isOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {licensePopup.companyName} - 청구 라이선스 수량
                </h3>
                <button
                  onClick={closeLicensePopup}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  청구 라이선스 수량을 입력해주세요
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="1"
                    value={licensePopup.licenseCount}
                    onChange={(e) => setLicensePopup(prev => ({
                      ...prev,
                      licenseCount: parseInt(e.target.value) || 40
                    }))}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="40"
                  />
                  <span className="text-gray-600">개</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  기본값: 40개 (필요에 따라 수정 가능)
                </p>
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={closeLicensePopup}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
                >
                  취소
                </button>
                <button
                  onClick={handleLicenseConfirm}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  확인
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BillingAutomationAdmin;