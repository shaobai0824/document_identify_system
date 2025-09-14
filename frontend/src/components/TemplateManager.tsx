import React, { useEffect, useState } from 'react';
import { Template } from '../App';
import CreateTemplateModal from './CreateTemplateModal';
import './TemplateManager.css';

interface TemplateManagerProps {
  onTemplateSelect: (template: Template) => void;
  onEditTemplate: (template: Template) => void;
}

const TemplateManager: React.FC<TemplateManagerProps> = ({ onTemplateSelect, onEditTemplate }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // 從 API 獲取範本列表
  const fetchTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/v1/document-templates');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setTemplates(data.data || []);
    } catch (err) {
      setError('載入範本失敗，請稍後再試。');
      console.error('Failed to fetch templates:', err);
      setTemplates([]); // 發生錯誤時清空範本，避免顯示舊資料
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  // 建立新範本
  const handleCreateTemplate = async (templateData: { name: string }) => {
    try {
      const response = await fetch('/api/v1/document-templates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: templateData.name }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      setShowCreateModal(false);
      await fetchTemplates(); // 重新載入列表以顯示新範本
    } catch (err) {
      console.error('Failed to create template:', err);
      // 可以在此處加入錯誤提示給使用者
    }
  };

  // 刪除範本
  const handleDeleteTemplate = async (templateId: string) => {
    if (!window.confirm('確定要刪除此範本嗎？此操作無法撤銷。')) return;
    
    try {
      const response = await fetch(`/api/v1/document-templates/${templateId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await fetchTemplates(); // 重新載入列表
    } catch (err) {
      console.error('Failed to delete template:', err);
      // 可以在此處加入錯誤提示給使用者
    }
  };

  const filteredTemplates = templates.filter(template =>
    template.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="template-manager">
        <div className="loading-container">
          <div className="loading"></div>
          <p>載入範本中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="template-manager">
        <div className="alert alert-error">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="template-manager">
      <div className="template-header">
        <div className="header-content">
          <h2>範本管理</h2>
          <p>管理文件驗證範本，定義欄位位置與驗證規則</p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          <span>+</span>
          建立範本
        </button>
      </div>

      <div className="template-controls">
        <div className="search-bar">
          <input
            type="text"
            placeholder="搜尋範本..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input"
          />
        </div>
        <div className="template-stats">
          總計 {filteredTemplates.length} 個範本
        </div>
      </div>

      <div className="templates-grid">
        {filteredTemplates.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>尚無範本</h3>
            <p>點擊「建立範本」開始建立您的第一個文件驗證範本</p>
            <button 
              className="btn btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              建立範本
            </button>
          </div>
        ) : (
          filteredTemplates.map((template) => (
            <div key={template.id} className="template-card card">
              <div className="card-header">
                <div className="template-title">
                  <h3 className="card-title">{template.name}</h3>
                  <span className={`status ${template.status}`}>
                    {template.status === 'active' ? '啟用' : '停用'}
                  </span>
                </div>
                <div className="template-meta">
                  版本 {template.version} • {template.field_definitions.length} 個欄位
                </div>
              </div>
              
              <div className="card-body">
                <div className="template-info">
                  <div className="info-item">
                    <span className="label">建立日期:</span>
                    <span className="value">
                      {new Date(template.created_at).toLocaleDateString('zh-TW')}
                    </span>
                  </div>
                  {template.updated_at && (
                    <div className="info-item">
                      <span className="label">更新日期:</span>
                      <span className="value">
                        {new Date(template.updated_at).toLocaleDateString('zh-TW')}
                      </span>
                    </div>
                  )}
                </div>
                
                {template.field_definitions.length > 0 && (
                  <div className="field-preview">
                    <h4>欄位預覽</h4>
                    <div className="field-list">
                      {template.field_definitions.slice(0, 3).map((field) => (
                        <span key={field.id} className="field-tag">
                          {field.name}
                          {field.required && <span className="required">*</span>}
                        </span>
                      ))}
                      {template.field_definitions.length > 3 && (
                        <span className="field-tag more">
                          +{template.field_definitions.length - 3} 更多
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
              
              <div className="card-footer">
                <button 
                  className="btn btn-secondary"
                  onClick={() => onTemplateSelect(template)}
                >
                  選擇
                </button>
                <button 
                  className="btn btn-primary"
                  onClick={async () => {
                    // 重新載入範本完整資料
                    try {
                      const response = await fetch(`/api/v1/document-templates/${template.id}`);
                      if (response.ok) {
                        const fullTemplate = await response.json();
                        onEditTemplate(fullTemplate);
                      } else {
                        console.error('Failed to load template details');
                        onEditTemplate(template); // 使用現有資料作為備案
                      }
                    } catch (error) {
                      console.error('Error loading template details:', error);
                      onEditTemplate(template); // 使用現有資料作為備案
                    }
                  }}
                >
                  編輯
                </button>
                <button 
                  className="btn btn-danger"
                  onClick={() => handleDeleteTemplate(template.id)}
                >
                  刪除
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {showCreateModal && (
        <CreateTemplateModal
          onSubmit={handleCreateTemplate}
          onCancel={() => setShowCreateModal(false)}
        />
      )}
    </div>
  );
};

export default TemplateManager;
