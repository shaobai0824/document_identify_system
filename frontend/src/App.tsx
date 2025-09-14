import { useState } from 'react';
import './App.css';

// 組件
import DocumentProcessor from './components/DocumentProcessor';
import FieldEditor from './components/FieldEditor';
import Sidebar from './components/Sidebar';
import TemplateManager from './components/TemplateManager';

// 類型定義
export interface Template {
  id: string;
  name: string;
  base_image_url?: string;
  field_definitions: FieldDefinition[];
  version: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface FieldDefinition {
  id: string;
  name: string;
  bbox: BoundingBox;
  required: boolean;
  suggested: boolean;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

function App() {
  const [activeTab, setActiveTab] = useState<'templates' | 'process' | 'editor'>('templates');
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);

  return (
    <div className="app">
      <div className="app-header">
        <h1>文件驗證系統</h1>
        <p>智慧文件處理與驗證平台</p>
      </div>
      
      <div className="app-body">
        <Sidebar 
          activeTab={activeTab} 
          onTabChange={setActiveTab}
          selectedTemplate={selectedTemplate}
        />
        
        <div className="main-content">
          {activeTab === 'templates' && (
            <TemplateManager 
              onTemplateSelect={setSelectedTemplate}
              onEditTemplate={(template: Template) => {
                setSelectedTemplate(template);
                setActiveTab('editor');
              }}
            />
          )}
          
          {activeTab === 'process' && (
            <DocumentProcessor selectedTemplate={selectedTemplate} />
          )}
          
          {activeTab === 'editor' && selectedTemplate && (
            <FieldEditor 
              template={selectedTemplate}
              onTemplateUpdate={setSelectedTemplate}
              onBack={() => setActiveTab('templates')}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
