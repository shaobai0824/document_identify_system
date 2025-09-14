import React, { useState } from 'react';
import { Template } from '../App';
import './ValidationResultDisplay.css';

interface ValidationResult {
  document_id: string;
  status: string;
  validation_result?: {
    is_success: boolean;
    missing_fields: Array<{
      field_name: string;
      bbox: { x1: number; y1: number; x2: number; y2: number };
    }>;
    extracted_data: Record<string, any>;
    per_field_confidence: Record<string, number>;
  };
  ocr_blocks?: Array<{
    page: number;
    bbox: { x1: number; y1: number; x2: number; y2: number };
    text: string;
    confidence: number;
  }>;
}

interface ValidationResultDisplayProps {
  result: ValidationResult;
  template: Template;
  onReset: () => void;
}

const ValidationResultDisplay: React.FC<ValidationResultDisplayProps> = ({ 
  result, 
  template, 
  onReset 
}) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'details' | 'ocr'>('summary');
  const [showExportModal, setShowExportModal] = useState(false);

  const validation = result.validation_result;
  if (!validation) return null;

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return '#48bb78';
    if (confidence >= 0.7) return '#ed8936';
    return '#f56565';
  };

  const getConfidenceText = (confidence: number) => {
    if (confidence >= 0.9) return '高';
    if (confidence >= 0.7) return '中';
    return '低';
  };

  const exportData = async (format: 'json' | 'csv' | 'xlsx') => {
    try {
      // TODO: 實作資料匯出功能
      const data = {
        document_id: result.document_id,
        template: template.name,
        extracted_data: validation.extracted_data,
        validation_status: validation.is_success ? 'passed' : 'failed',
        missing_fields: validation.missing_fields.map(f => f.field_name),
        confidence_scores: validation.per_field_confidence
      };

      // 模擬匯出
      const blob = new Blob([JSON.stringify(data, null, 2)], { 
        type: 'application/json' 
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `validation_result_${result.document_id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      
      setShowExportModal(false);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div className="validation-result">
      <div className="result-header">
        <div className="result-status">
          <div className={`status-badge ${validation.is_success ? 'success' : 'warning'}`}>
            {validation.is_success ? '✅ 驗證通過' : '⚠️ 需要注意'}
          </div>
          <div className="document-id">文件 ID: {result.document_id}</div>
        </div>
        
        <div className="result-actions">
          <button 
            className="btn btn-secondary"
            onClick={() => setShowExportModal(true)}
          >
            📊 匯出結果
          </button>
          <button 
            className="btn btn-primary"
            onClick={onReset}
          >
            🔄 處理新文件
          </button>
        </div>
      </div>

      <div className="result-tabs">
        <button 
          className={`tab ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          摘要
        </button>
        <button 
          className={`tab ${activeTab === 'details' ? 'active' : ''}`}
          onClick={() => setActiveTab('details')}
        >
          詳細資料
        </button>
        <button 
          className={`tab ${activeTab === 'ocr' ? 'active' : ''}`}
          onClick={() => setActiveTab('ocr')}
        >
          OCR 結果
        </button>
      </div>

      <div className="result-content">
        {activeTab === 'summary' && (
          <div className="summary-tab">
            <div className="summary-grid">
              <div className="summary-card">
                <h3>驗證狀態</h3>
                <div className="summary-value">
                  {validation.is_success ? '通過' : '未通過'}
                </div>
                <div className="summary-desc">
                  {validation.is_success 
                    ? '所有必要欄位都已正確識別'
                    : `${validation.missing_fields.length} 個欄位需要檢查`
                  }
                </div>
              </div>

              <div className="summary-card">
                <h3>識別欄位</h3>
                <div className="summary-value">
                  {Object.keys(validation.extracted_data).length} / {template.field_definitions.length}
                </div>
                <div className="summary-desc">
                  成功識別的欄位數量
                </div>
              </div>

              <div className="summary-card">
                <h3>平均信心度</h3>
                <div className="summary-value">
                  {(Object.values(validation.per_field_confidence).reduce((a, b) => a + b, 0) / 
                    Object.values(validation.per_field_confidence).length * 100).toFixed(1)}%
                </div>
                <div className="summary-desc">
                  OCR 識別的平均信心度
                </div>
              </div>
            </div>

            {validation.missing_fields.length > 0 && (
              <div className="missing-fields-section">
                <h3>缺漏或低信心度欄位</h3>
                <div className="missing-fields-list">
                  {validation.missing_fields.map((field, index) => (
                    <div key={index} className="missing-field">
                      <span className="field-name">{field.field_name}</span>
                      <span className="field-reason">需要人工檢查</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'details' && (
          <div className="details-tab">
            <h3>擷取的資料</h3>
            <div className="extracted-data">
              {Object.entries(validation.extracted_data).map(([field, value]) => (
                <div key={field} className="data-item">
                  <div className="data-header">
                    <span className="field-name">{field}</span>
                    <div className="confidence-info">
                      <span 
                        className="confidence-badge"
                        style={{ 
                          backgroundColor: getConfidenceColor(validation.per_field_confidence[field] || 0),
                          color: 'white'
                        }}
                      >
                        {getConfidenceText(validation.per_field_confidence[field] || 0)}信心度
                      </span>
                      <span className="confidence-value">
                        {((validation.per_field_confidence[field] || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="data-value">{String(value)}</div>
                </div>
              ))}
            </div>

            <h3>範本欄位對照</h3>
            <div className="field-mapping">
              {template.field_definitions.map((field) => {
                const hasData = field.name in validation.extracted_data;
                const confidence = validation.per_field_confidence[field.name] || 0;
                
                return (
                  <div key={field.id} className={`mapping-item ${!hasData ? 'missing' : ''}`}>
                    <div className="mapping-header">
                      <span className="field-name">
                        {field.name}
                        {field.required && <span className="required">*</span>}
                      </span>
                      <span className={`status ${hasData ? 'found' : 'missing'}`}>
                        {hasData ? '✓ 已識別' : '✗ 未識別'}
                      </span>
                    </div>
                    {hasData && (
                      <div className="mapping-details">
                        <div className="extracted-value">
                          {String(validation.extracted_data[field.name])}
                        </div>
                        <div className="confidence-bar">
                          <div 
                            className="confidence-fill"
                            style={{ 
                              width: `${confidence * 100}%`,
                              backgroundColor: getConfidenceColor(confidence)
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === 'ocr' && (
          <div className="ocr-tab">
            <h3>OCR 識別區塊</h3>
            {result.ocr_blocks && result.ocr_blocks.length > 0 ? (
              <div className="ocr-blocks">
                {result.ocr_blocks.map((block, index) => (
                  <div key={index} className="ocr-block">
                    <div className="block-header">
                      <span className="block-info">
                        頁面 {block.page} | 座標 ({block.bbox.x1}, {block.bbox.y1}) - ({block.bbox.x2}, {block.bbox.y2})
                      </span>
                      <span 
                        className="confidence-badge"
                        style={{ 
                          backgroundColor: getConfidenceColor(block.confidence),
                          color: 'white'
                        }}
                      >
                        {(block.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="block-text">{block.text}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-ocr-data">
                <p>無可用的 OCR 區塊資料</p>
              </div>
            )}
          </div>
        )}
      </div>

      {showExportModal && (
        <div className="modal-overlay" onClick={() => setShowExportModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>匯出驗證結果</h3>
              <button className="modal-close" onClick={() => setShowExportModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <p>選擇匯出格式：</p>
              <div className="export-options">
                <button 
                  className="btn btn-secondary"
                  onClick={() => exportData('json')}
                >
                  📄 JSON
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => exportData('csv')}
                >
                  📊 CSV
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => exportData('xlsx')}
                >
                  📈 Excel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ValidationResultDisplay;
