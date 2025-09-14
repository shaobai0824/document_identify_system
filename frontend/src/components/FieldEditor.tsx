import { Modal } from 'antd';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Document, Page } from 'react-pdf';
import { BoundingBox, FieldDefinition, Template } from '../App';
import './FieldEditor.css';

// Import pdfjs from pdfjs-dist directly
import * as pdfjs from 'pdfjs-dist';

// Set the worker path to use the local worker file
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

interface FieldEditorProps {
  template: Template;
  onTemplateUpdate: (template: Template) => void;
  onBack: () => void;
}


interface DrawingBox {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  isDrawing: boolean;
}

// Helper to get canvas relative coordinates
const getCoords = (e: any, ref: React.RefObject<HTMLCanvasElement | null>): { x: number, y: number } | null => {
  const rect = ref.current?.getBoundingClientRect();
  if (!rect) return null;
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
  };
};

const FieldEditor: React.FC<FieldEditorProps> = ({ template, onTemplateUpdate, onBack }) => {
  const [selectedField, setSelectedField] = useState<FieldDefinition | null>(null);
  const [drawingBox, setDrawingBox] = useState<DrawingBox | null>(null);
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [showFieldModal, setShowFieldModal] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldRequired, setNewFieldRequired] = useState(false);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileType, setFileType] = useState<'image' | 'pdf' | null>(null);
  const [imageScale, setImageScale] = useState(1);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [unsavedFile, setUnsavedFile] = useState<File | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 當範本載入時，自動載入範本的檔案和欄位定義
  useEffect(() => {
    // 載入範本的底圖（只有在沒有當前檔案時才載入）
    if (template.base_image_url && !fileUrl) {
      setFileUrl(template.base_image_url);
      // 根據 URL 判斷檔案類型
      if (template.base_image_url.toLowerCase().includes('.pdf')) {
        setFileType('pdf');
      } else {
        setFileType('image');
      }
      setImageScale(1);
    } else if (template.base_image_url && fileUrl !== template.base_image_url) {
      // 如果範本的 base_image_url 與當前不同，更新檔案
      setFileUrl(template.base_image_url);
      if (template.base_image_url.toLowerCase().includes('.pdf')) {
        setFileType('pdf');
      } else {
        setFileType('image');
      }
      setImageScale(1);
    }
    
  }, [template, onTemplateUpdate]);

  const handleFileUpload = useCallback((uploadedFile: File) => {
    const url = URL.createObjectURL(uploadedFile);
    setFileUrl(url);
    setFileType(uploadedFile.type === 'application/pdf' ? 'pdf' : 'image');
    setImageScale(1);
    setUnsavedFile(uploadedFile); // 標記為未儲存
    setHasUnsavedChanges(true); // 標記為有未儲存變更
  }, []);

  const saveTemplateImage = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`/api/v1/document-templates/${template.id}/image`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Failed to save template image');
      }
      
      const updatedTemplate = await response.json();
      onTemplateUpdate(updatedTemplate);
      
      // 更新本地狀態
      setFileUrl(updatedTemplate.base_image_url);
      setUnsavedFile(null); // 清除未儲存標記
      setHasUnsavedChanges(false);
      
      alert('範本圖片已儲存到資料庫！');
    } catch (error) {
      console.error('Error saving template image:', error);
      alert('儲存失敗，請重試');
    }
  };


  // 儲存欄位變更到資料庫
  const saveFieldChanges = async () => {
    try {
      const response = await fetch(`/api/v1/document-templates/${template.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: template.name,
          field_definitions: template.field_definitions
        }),
      });
      
      if (response.ok) {
        const updatedTemplate = await response.json();
        onTemplateUpdate(updatedTemplate); // 更新本地範本資料
        setHasUnsavedChanges(false);
        alert('欄位變更已儲存到資料庫！');
      } else {
        console.error('欄位儲存失敗:', response.statusText);
        alert('欄位儲存失敗，請重試');
      }
    } catch (error) {
      console.error('欄位儲存錯誤:', error);
      alert('欄位儲存失敗，請重試');
    }
  };

  const drawOverlays = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    // Clear the overlay canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw existing field boxes
    template.field_definitions.forEach((field) => {
      const bbox = field.bbox;
      const x = bbox.x1 * imageScale;
      const y = bbox.y1 * imageScale;
      const width = (bbox.x2 - bbox.x1) * imageScale;
      const height = (bbox.y2 - bbox.y1) * imageScale;

      ctx.strokeStyle = field === selectedField ? '#667eea' : '#48bb78';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);
      ctx.fillStyle = field === selectedField ? 'rgba(102, 126, 234, 0.2)' : 'rgba(72, 187, 120, 0.2)';
      ctx.fillRect(x, y, width, height);
      ctx.fillStyle = field === selectedField ? '#667eea' : '#48bb78';
      ctx.font = '12px Arial';
      ctx.fillText(field.name, x, y - 5);
    });

    // Draw the box currently being drawn
    if (drawingBox && drawingBox.isDrawing) {
      const x = Math.min(drawingBox.startX, drawingBox.endX);
      const y = Math.min(drawingBox.startY, drawingBox.endY);
      const width = Math.abs(drawingBox.endX - drawingBox.startX);
      const height = Math.abs(drawingBox.endY - drawingBox.startY);
      ctx.strokeStyle = '#f56565';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);
      ctx.fillStyle = 'rgba(245, 101, 101, 0.2)';
      ctx.fillRect(x, y, width, height);
    }
  }, [template.field_definitions, selectedField, drawingBox, imageScale]);

  useEffect(() => {
    drawOverlays();
  }, [drawOverlays]);

  const onImageLoad = (event: any) => {
    setNaturalSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight });
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('PDF 文件載入成功，頁數:', numPages);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF 文件載入失敗:', error);
  };

  const onPageLoadSuccess = (page: any) => {
    console.log('PDF 頁面載入成功，原始尺寸:', page.width, 'x', page.height);
    console.log('當前縮放比例:', imageScale);
    console.log('計算後尺寸:', page.width * imageScale, 'x', page.height * imageScale);
    
    // PDF 頁面的原始尺寸，不包含縮放
    setNaturalSize({ 
      width: page.width, 
      height: page.height 
    });
  };

  const onPageLoadError = (error: Error) => {
    console.error('PDF 頁面載入失敗:', error);
  };

  const handleMouseDown = (e: any) => {
    if (!isDrawingMode || !overlayCanvasRef.current) return;
    const coords = getCoords(e, overlayCanvasRef);
    if (!coords) return;
    setDrawingBox({ startX: coords.x, startY: coords.y, endX: coords.x, endY: coords.y, isDrawing: true });
  };

  const handleMouseMove = (e: any) => {
    if (!drawingBox?.isDrawing || !overlayCanvasRef.current) return;
    const coords = getCoords(e, overlayCanvasRef);
    if (!coords) return;
    setDrawingBox(prev => prev ? { ...prev, endX: coords.x, endY: coords.y } : null);
  };

  const handleMouseUp = () => {
    if (!drawingBox?.isDrawing) return;
    const width = Math.abs(drawingBox.endX - drawingBox.startX);
    const height = Math.abs(drawingBox.endY - drawingBox.startY);
    if (width < 10 || height < 10) {
      setDrawingBox(null);
      return;
    }
    setShowFieldModal(true);
  };

  const handleCanvasClick = (e: any) => {
    if (isDrawingMode || !overlayCanvasRef.current) return;
    const coords = getCoords(e, overlayCanvasRef);
    if (!coords) return;

    const foundField = template.field_definitions.find(field => {
      const bbox = field.bbox;
      const fieldX = bbox.x1 * imageScale;
      const fieldY = bbox.y1 * imageScale;
      const fieldWidth = (bbox.x2 - bbox.x1) * imageScale;
      const fieldHeight = (bbox.y2 - bbox.y1) * imageScale;
      return coords.x >= fieldX && coords.x <= fieldX + fieldWidth && coords.y >= fieldY && coords.y <= fieldY + fieldHeight;
    });
    setSelectedField(foundField || null);
  };

  const addField = async () => {
    if (!drawingBox || !newFieldName.trim()) return;
    const bbox: BoundingBox = {
      x1: Math.min(drawingBox.startX, drawingBox.endX) / imageScale,
      y1: Math.min(drawingBox.startY, drawingBox.endY) / imageScale,
      x2: Math.max(drawingBox.startX, drawingBox.endX) / imageScale,
      y2: Math.max(drawingBox.startY, drawingBox.endY) / imageScale,
    };
    const newField: FieldDefinition = {
      id: Date.now().toString(),
      name: newFieldName.trim(),
      bbox,
      required: newFieldRequired,
      suggested: false
    };
    
    const updatedTemplate = { 
      ...template, 
      field_definitions: [...template.field_definitions, newField],
      base_image_url: template.base_image_url // 確保保留 base_image_url
    };
    
    // 更新本地狀態
    onTemplateUpdate(updatedTemplate);
    setHasUnsavedChanges(true); // 標記為有未儲存變更
    
    // 可選：保存到後端（現在改為手動儲存）
    // try {
    //   const response = await fetch(`/api/v1/document-templates/${template.id}`, {
    //     method: 'PUT',
    //     headers: {
    //       'Content-Type': 'application/json',
    //     },
    //     body: JSON.stringify(updatedTemplate),
    //   });
    //   
    //   if (response.ok) {
    //     console.log('欄位保存成功');
    //     setHasUnsavedChanges(false);
    //   } else {
    //     console.error('欄位保存失敗:', response.statusText);
    //   }
    // } catch (error) {
    //   console.error('欄位保存錯誤:', error);
    // }
    
    setDrawingBox(null);
    setShowFieldModal(false);
    setNewFieldName('');
    setNewFieldRequired(false);
    setIsDrawingMode(false);
  };
  
  const deleteField = async (fieldId: string) => {
    Modal.confirm({
      title: '確認刪除',
      content: '確定要刪除此欄位嗎？此操作無法撤銷。',
      okText: '確定',
      cancelText: '取消',
      onOk: async () => {
        const updatedTemplate = { 
          ...template, 
          field_definitions: template.field_definitions.filter(f => f.id !== fieldId),
          base_image_url: template.base_image_url // 確保保留 base_image_url
        };
        
        // 更新本地狀態
        onTemplateUpdate(updatedTemplate);
        setHasUnsavedChanges(true); // 標記為有未儲存變更
        
        // 可選：保存到後端（現在改為手動儲存）
        // try {
        //   const response = await fetch(`/api/v1/document-templates/${template.id}`, {
        //     method: 'PUT',
        //     headers: {
        //       'Content-Type': 'application/json',
        //     },
        //     body: JSON.stringify(updatedTemplate),
        //   });
        //   
        //   if (response.ok) {
        //     console.log('欄位刪除成功');
        //     setHasUnsavedChanges(false);
        //   } else {
        //     console.error('欄位刪除失敗:', response.statusText);
        //   }
        // } catch (error) {
        //   console.error('欄位刪除錯誤:', error);
        // }
        
        setSelectedField(null);
      },
    });
  };

  return (
    <div className="field-editor">
      <div className="editor-header">
        {/* Header content remains the same */}
        <div className="header-left">
          <button className="btn btn-secondary" onClick={onBack}>← 返回</button>
          <div className="template-info">
            <h2>{template.name} - 欄位編輯器</h2>
            <p>定義文件中需要驗證的欄位位置</p>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()}>📷 上傳底圖</button>
          
          {/* 儲存欄位變更按鈕 */}
          {hasUnsavedChanges && (
            <button 
              className="btn btn-success" 
              onClick={saveFieldChanges}
            >
              💾 儲存欄位變更
            </button>
          )}
          
          {/* 儲存圖片到資料庫按鈕 */}
          {unsavedFile && (
            <button 
              className="btn btn-primary" 
              onClick={() => saveTemplateImage(unsavedFile)}
            >
              🗄️ 儲存圖片到資料庫
            </button>
          )}
        </div>
      </div>
      <div className="editor-body">
        <div className="editor-main">
          <div className="editor-toolbar">
            <button className={`btn ${isDrawingMode ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setIsDrawingMode(!isDrawingMode)} disabled={!fileUrl}>
              {isDrawingMode ? '✏️ 繪製模式' : '👆 選擇模式'}
            </button>
            <div className="zoom-controls">
              <button className="btn btn-secondary" onClick={() => setImageScale(s => Math.max(0.1, s - 0.1))} disabled={!fileUrl}>🔍-</button>
              <span className="zoom-level">{Math.round(imageScale * 100)}%</span>
              <button className="btn btn-secondary" onClick={() => setImageScale(s => Math.min(3, s + 0.1))} disabled={!fileUrl}>🔍+</button>
            </div>
          </div>
          <div className="canvas-container" ref={containerRef}>
            {fileUrl ? (
              <div style={{ position: 'relative', width: naturalSize.width * imageScale, height: naturalSize.height * imageScale }}>
                {fileType === 'image' && (
                  <img
                    src={fileUrl}
                    onLoad={onImageLoad}
                    alt="Template"
                    style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
                  />
                )}
                {fileType === 'pdf' && (
                  <div style={{ 
                    position: 'absolute', 
                    top: 0, 
                    left: 0,
                    minWidth: '400px',
                    minHeight: '600px',
                    backgroundColor: 'transparent',
                    border: '1px solid #e2e8f0',
                    zIndex: 5
                  }}>
                    <Document 
                      file={fileUrl} 
                      onLoadSuccess={onDocumentLoadSuccess}
                      onLoadError={onDocumentLoadError}
                    >
                      <Page 
                        pageNumber={1} 
                        scale={imageScale} 
                        onLoadSuccess={onPageLoadSuccess}
                        onLoadError={onPageLoadError}
                        renderTextLayer={false}
                        renderAnnotationLayer={false}
                      />
                    </Document>
                  </div>
                )}
                <canvas
                  ref={overlayCanvasRef}
                  width={naturalSize.width * imageScale}
                  height={naturalSize.height * imageScale}
                  className={`editor-canvas ${isDrawingMode ? 'drawing-mode' : 'select-mode'}`}
                  style={{ position: 'absolute', top: 0, left: 0, zIndex: 10, pointerEvents: isDrawingMode ? 'auto' : 'none' }}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onClick={handleCanvasClick}
                />
              </div>
            ) : (
              <div className="no-image">
                <div className="no-image-icon">🖼️</div>
                <h3>請上傳範本底圖</h3>
                <p>上傳文件範本 (圖片或 PDF)，然後在上面繪製欄位框</p>
                <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>選擇檔案</button>
              </div>
            )}
          </div>
        </div>
        <div className="editor-sidebar">
            {/* Sidebar remains the same */}
            <div className="sidebar-section">
            <h3>欄位列表 ({template.field_definitions.length})</h3>
            <div className="field-list">
              {template.field_definitions.length === 0 ? (
                <div className="empty-fields">
                  <p>尚未定義任何欄位</p>
                  <p>使用繪製模式在圖片上畫出欄位框</p>
                </div>
              ) : (
                template.field_definitions.map((field) => (
                  <div key={field.id} className={`field-item ${field === selectedField ? 'selected' : ''} ${field.suggested ? 'suggested' : ''}`} onClick={() => setSelectedField(field)}>
                    <div className="field-header">
                      <span className="field-name">{field.name}</span>
                      {field.required && <span className="required">*</span>}
                      {field.suggested && <span className="suggested-badge">AI</span>}
                    </div>
                    <div className="field-coords">
                      ({Math.round(field.bbox.x1)}, {Math.round(field.bbox.y1)}) - ({Math.round(field.bbox.x2)}, {Math.round(field.bbox.y2)})
                    </div>
                    <div className="field-actions">
                      <button className="btn-small btn-danger" onClick={(e) => { e.stopPropagation(); deleteField(field.id); }}>刪除</button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          {selectedField && (
            <div className="sidebar-section">
              <h3>欄位詳情</h3>
              <div className="field-details">
                <div className="detail-item"><label>名稱:</label><span>{selectedField.name}</span></div>
                <div className="detail-item"><label>必填:</label><span>{selectedField.required ? '是' : '否'}</span></div>
                <div className="detail-item"><label>座標:</label><span>({Math.round(selectedField.bbox.x1)}, {Math.round(selectedField.bbox.y1)}) - ({Math.round(selectedField.bbox.x2)}, {Math.round(selectedField.bbox.y2)})</span></div>
                <div className="detail-item"><label>大小:</label><span>{Math.round(selectedField.bbox.x2 - selectedField.bbox.x1)} × {Math.round(selectedField.bbox.y2 - selectedField.bbox.y1)} px</span></div>
              </div>
            </div>
          )}
        </div>
      </div>
      <input ref={fileInputRef} type="file" accept="image/*,application/pdf" onChange={(e) => { if (e.target.files?.[0]) { handleFileUpload(e.target.files[0]); } }} style={{ display: 'none' }} />
      {showFieldModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>新增欄位</h3>
              <button className="modal-close" onClick={() => { setShowFieldModal(false); setDrawingBox(null); }}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">欄位名稱 <span className="required">*</span></label>
                <input type="text" className="form-input" value={newFieldName} onChange={(e) => setNewFieldName(e.target.value)} autoFocus />
              </div>
              <div className="form-group">
                <label className="checkbox-label"><input type="checkbox" checked={newFieldRequired} onChange={(e) => setNewFieldRequired(e.target.checked)} /> 必填欄位</label>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => { setShowFieldModal(false); setDrawingBox(null); }}>取消</button>
              <button className="btn btn-primary" onClick={addField} disabled={!newFieldName.trim()}>新增欄位</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FieldEditor;