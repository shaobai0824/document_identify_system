import React, { useState } from 'react';
import './CreateTemplateModal.css';

interface CreateTemplateModalProps {
  onSubmit: (data: { name: string }) => void;
  onCancel: () => void;
}

const CreateTemplateModal: React.FC<CreateTemplateModalProps> = ({ onSubmit, onCancel }) => {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      await onSubmit({ name: name.trim() });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>建立新範本</h3>
          <button className="modal-close" onClick={onCancel}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label" htmlFor="template-name">
                範本名稱 <span className="required">*</span>
              </label>
              <input
                id="template-name"
                type="text"
                className="form-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：身分證範本、護照範本..."
                required
                autoFocus
              />
              <div className="form-help">
                請輸入描述性的範本名稱，方便後續識別和管理
              </div>
            </div>
          </div>
          
          <div className="modal-footer">
            <button 
              type="button" 
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={loading}
            >
              取消
            </button>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={!name.trim() || loading}
            >
              {loading && <span className="loading"></span>}
              建立範本
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateTemplateModal;
