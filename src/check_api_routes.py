#!/usr/bin/env python3
"""
檢查 API 路由註冊
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

def check_routes():
    """檢查所有路由是否正確註冊"""
    print("🔍 檢查 API 路由註冊...\n")
    
    try:
        from verifier_app.main import app

        # 取得所有路由
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    if method != 'HEAD':  # 忽略 HEAD 方法
                        routes.append(f"{method} {route.path}")
        
        # 按路徑排序
        routes.sort()
        
        # 分類顯示路由
        categories = {
            "健康檢查": [],
            "範本管理": [],
            "文件處理": [],
            "版本管理": [],
            "上傳管理": [],
            "系統設定": [],
            "分類檢測": [],
            "安全檢測": [],
            "Webhook": [],
            "WebSocket": [],
            "審核流程": [],
            "其他": []
        }
        
        for route in routes:
            if "health" in route.lower():
                categories["健康檢查"].append(route)
            elif "document-templates" in route.lower() or "templates" in route.lower():
                categories["範本管理"].append(route)
            elif "process" in route.lower() or "documents" in route.lower() or "upload" in route.lower():
                if "uploads/presign" in route.lower() or "uploads/complete" in route.lower():
                    categories["上傳管理"].append(route)
                else:
                    categories["文件處理"].append(route)
            elif "versions" in route.lower():
                categories["版本管理"].append(route)
            elif "settings" in route.lower():
                categories["系統設定"].append(route)
            elif "classification" in route.lower() or "barcodes" in route.lower():
                categories["分類檢測"].append(route)
            elif "signatures" in route.lower() or "tamper" in route.lower() or "audit" in route.lower():
                categories["安全檢測"].append(route)
            elif "webhooks" in route.lower():
                categories["Webhook"].append(route)
            elif "ws" in route.lower():
                categories["WebSocket"].append(route)
            elif "review" in route.lower():
                categories["審核流程"].append(route)
            else:
                categories["其他"].append(route)
        
        # 顯示結果
        total_routes = 0
        for category, routes_list in categories.items():
            if routes_list:
                print(f"📋 {category} ({len(routes_list)} 個端點):")
                for route in routes_list:
                    print(f"   ✅ {route}")
                print()
                total_routes += len(routes_list)
        
        print(f"🎯 總計: {total_routes} 個 API 端點已註冊")
        
        # 檢查關鍵端點
        required_endpoints = [
            "GET /v1/health",
            "POST /v1/document-templates",
            "GET /v1/document-templates",
            "POST /v1/process",
            "POST /v1/uploads/presign",
            "GET /v1/settings/processing",
            "POST /v1/classification",
            "POST /v1/webhooks"
        ]
        
        print("\n🔍 檢查關鍵端點:")
        missing_endpoints = []
        for endpoint in required_endpoints:
            if endpoint in routes:
                print(f"   ✅ {endpoint}")
            else:
                print(f"   ❌ {endpoint} - 缺少")
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"\n⚠️  發現 {len(missing_endpoints)} 個缺少的關鍵端點")
            return False
        else:
            print("\n🎉 所有關鍵端點都已正確註冊！")
            return True
            
    except ImportError as e:
        print(f"❌ 導入錯誤: {e}")
        print("請確保所有相依套件都已安裝")
        return False
    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_routes()
    print(f"\n{'='*50}")
    if success:
        print("✅ API 路由檢查通過！所有端點都已正確實作和註冊。")
    else:
        print("❌ API 路由檢查失敗！請檢查缺少的端點。")
    sys.exit(0 if success else 1)
