import React from 'react';
import { ArrowLeft } from 'lucide-react';

const TaxInvoicePage = ({ onBack }) => {
  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* 헤더 */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            뒤로가기
          </button>
          <h1 className="text-2xl font-bold text-gray-900">세금계산서 발행</h1>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <div className="text-center text-gray-500">
            <p className="text-lg mb-2">세금계산서 발행 기능</p>
            <p className="text-sm">이 기능은 현재 개발 중입니다.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaxInvoicePage;
