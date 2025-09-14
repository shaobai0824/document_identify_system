import React, { useRef, useState } from 'react';
import { Template } from '../App';
import './DocumentProcessor.css';
import ValidationResultDisplay from './ValidationResultDisplay';

interface DocumentProcessorProps {
  selectedTemplate: Template | null;
}

interface ProcessingResult {
  document_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
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

const DocumentProcessor: React.FC<DocumentProcessorProps> = ({ selectedTemplate }) => {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (selectedFile: File) => {
    // 驗證檔案類型
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError('不支援的檔案格式。請上傳 PNG、JPG 或 PDF 檔案。');
      return;
    }

    // 驗證檔案大小 (50MB)
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('檔案大小超過限制。請上傳小於 50MB 的檔案。');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setResult(null);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const processDocument = async () => {
    if (!file || !selectedTemplate) return;

    setProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('template_id', selectedTemplate.id);

      // TODO: 替換為實際 API 端點
      const response = await fetch('/api/v1/process', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('處理失敗');
      }

      const initialResult = await response.json();
      
      // 模擬處理結果（實際應該輪詢狀態）
      setTimeout(() => {
        const mockResult: ProcessingResult = {
          document_id: initialResult.document_id || 'doc_123',
          status: 'completed',
          validation_result: {
            is_success: false,
            missing_fields: [
              {
                field_name: '姓名',
                bbox: { x1: 100, y1: 50, x2: 300, y2: 80 }
              }
            ],
            extracted_data: {
              '身分證號': 'A123456789',
              '出生日期': '1990/01/01'
            },
            per_field_confidence: {
              '身分證號': 0.95,
              '出生日期': 0.87,
              '姓名': 0.32
            }
          },
          ocr_blocks: [
            {
              page: 1,
              bbox: { x1: 100, y1: 100, x2: 300, y2: 130 },
              text: 'A123456789',
              confidence: 0.95
            },
            {
              page: 1,
              bbox: { x1: 100, y1: 150, x2: 300, y2: 180 },
              text: '1990/01/01',
              confidence: 0.87
            }
          ]
        };
        setResult(mockResult);
        setProcessing(false);
      }, 3000);

    } catch (err) {
      setError(err instanceof Error ? err.message : '處理過程中發生錯誤');
      setProcessing(false);
    }
  };

  const resetProcessor = () => {
    setFile(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (!selectedTemplate) {
    return (
      <div className="document-processor">
        <div className="no-template">
          <div className="no-template-icon">📋</div>
          <h3>請先選擇範本</h3>
          <p>請到「範本管理」頁面選擇一個範本，然後回到此處處理文件。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="document-processor">
      <div className="processor-header">
        <h2>文件處理</h2>
        <p>上傳文件進行 OCR 識別與驗證</p>
        <div className="selected-template-info">
          <span className="template-badge">使用範本: {selectedTemplate.name}</span>
          <span className="field-count">{selectedTemplate.field_definitions.length} 個驗證欄位</span>
        </div>
      </div>

      {!result ? (
        <div className="upload-section">
          <div 
            className={`upload-area ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf"
              onChange={handleFileInputChange}
              style={{ display: 'none' }}
            />
            
            {!file ? (
              <div className="upload-placeholder">
                <div className="upload-icon">📁</div>
                <h3>拖放文件到此處或點擊上傳</h3>
                <p>支援 PNG、JPG、PDF 格式，最大 50MB</p>
                <button className="btn btn-primary">選擇檔案</button>
              </div>
            ) : (
              <div className="file-info">
                <div className="file-icon">📄</div>
                <div className="file-details">
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">
                    {(file.size / 1024 / 1024).toFixed(2)} MB • {file.type}
                  </div>
                </div>
                <button 
                  className="file-remove"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                >
                  ×
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          {file && (
            <div className="process-actions">
              <button 
                className="btn btn-primary"
                onClick={processDocument}
                disabled={processing}
              >
                {processing && <span className="loading"></span>}
                {processing ? '處理中...' : '開始處理'}
              </button>
              <button 
                className="btn btn-secondary"
                onClick={resetProcessor}
                disabled={processing}
              >
                重新選擇
              </button>
            </div>
          )}

          {processing && (
            <div className="processing-status">
              <div className="processing-steps">
                <div className="step active">
                  <span className="step-icon">📤</span>
                  <span className="step-text">上傳檔案</span>
                </div>
                <div className="step active">
                  <span className="step-icon">🔍</span>
                  <span className="step-text">OCR 識別</span>
                </div>
                <div className="step">
                  <span className="step-icon">✅</span>
                  <span className="step-text">驗證完成</span>
                </div>
              </div>
              <div className="processing-message">
                正在使用 OCR 技術識別文件內容，請稍候...
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="result-section">
          <ValidationResultDisplay 
            result={result}
            template={selectedTemplate}
            onReset={resetProcessor}
          />
        </div>
      )}
    </div>
  );
};

export default DocumentProcessor;
