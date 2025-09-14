import React from 'react';
import { Template } from '../App';
import './Sidebar.css';

interface SidebarProps {
  activeTab: 'templates' | 'process' | 'editor';
  onTabChange: (tab: 'templates' | 'process' | 'editor') => void;
  selectedTemplate: Template | null;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange, selectedTemplate }) => {
  return (
    <div className="sidebar">
      <div className="sidebar-section">
        <h3>主要功能</h3>
        <ul className="sidebar-menu">
          <li>
            <button 
              className={`sidebar-item ${activeTab === 'templates' ? 'active' : ''}`}
              onClick={() => onTabChange('templates')}
            >
              <span className="icon">📋</span>
              範本管理
            </button>
          </li>
          <li>
            <button 
              className={`sidebar-item ${activeTab === 'process' ? 'active' : ''}`}
              onClick={() => onTabChange('process')}
            >
              <span className="icon">📄</span>
              文件處理
            </button>
          </li>
          {selectedTemplate && (
            <li>
              <button 
                className={`sidebar-item ${activeTab === 'editor' ? 'active' : ''}`}
                onClick={() => onTabChange('editor')}
              >
                <span className="icon">✏️</span>
                欄位編輯器
              </button>
            </li>
          )}
        </ul>
      </div>

      {selectedTemplate && (
        <div className="sidebar-section">
          <h3>目前範本</h3>
          <div className="selected-template">
            <div className="template-info">
              <div className="template-name">{selectedTemplate.name}</div>
              <div className="template-meta">
                版本: {selectedTemplate.version} | 
                欄位數: {selectedTemplate.field_definitions.length}
              </div>
              <div className="template-status">
                狀態: <span className={`status ${selectedTemplate.status}`}>
                  {selectedTemplate.status === 'active' ? '啟用' : '停用'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="sidebar-section">
        <h3>系統狀態</h3>
        <div className="system-status">
          <div className="status-item">
            <span className="status-indicator online"></span>
            API 服務正常
          </div>
          <div className="status-item">
            <span className="status-indicator online"></span>
            OCR 服務正常
          </div>
          <div className="status-item">
            <span className="status-indicator online"></span>
            儲存服務正常
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
