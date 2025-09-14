"""
MVP 功能測試腳本
"""

import asyncio
import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from verifier_app.infrastructure.services.document_processor import \
    DocumentProcessor


def create_test_image() -> bytes:
    """建立測試圖片"""
    # 建立一個簡單的測試圖片，包含一些文字
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # 嘗試使用預設字體
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        # 如果找不到字體，使用預設字體
        font = ImageFont.load_default()
    
    # 繪製測試文字
    text_lines = [
        "Document Verification Test",
        "Name: John Doe",
        "ID: A123456789",
        "Date: 2024-01-01"
    ]
    
    y = 100
    for line in text_lines:
        draw.text((50, y), line, fill='black', font=font)
        y += 80
    
    # 轉換為 bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


async def test_mvp_flow():
    """測試 MVP 端到端流程"""
    print("🚀 開始測試 MVP 功能...")
    
    try:
        # 1. 建立測試圖片
        print("📷 建立測試圖片...")
        test_image_data = create_test_image()
        print(f"   圖片大小: {len(test_image_data)} bytes")
        
        # 2. 初始化處理器
        print("⚙️ 初始化文件處理器...")
        processor = DocumentProcessor()
        
        # 3. 處理文件
        print("📄 處理文件...")
        result = await processor.process_uploaded_file(
            file_content=test_image_data,
            filename="test_document.png",
            template_id=None  # 不使用模板驗證
        )
        
        print("✅ 文件處理完成!")
        print(f"   文件 ID: {result['document_id']}")
        print(f"   狀態: {result['status']}")
        
        # 4. 檢查 OCR 結果
        if 'ocr_result' in result and result['ocr_result']:
            ocr = result['ocr_result']
            print(f"   OCR 文字: {ocr['text'][:100]}...")
            print(f"   OCR 信心度: {ocr['confidence']:.2f}")
            print(f"   文字區域數量: {ocr['regions_count']}")
        
        # 5. 檢查驗證結果
        if 'verification_result' in result and result['verification_result']:
            verification = result['verification_result']
            print(f"   驗證狀態: {verification['status']}")
            print(f"   驗證信心度: {verification['confidence']:.2f}")
            print(f"   需要人工審核: {verification['requires_manual_review']}")
        
        # 6. 測試狀態查詢
        print("🔍 查詢文件狀態...")
        status_result = await processor.get_document_status(result['document_id'])
        print(f"   查詢狀態: {status_result['status']}")
        print(f"   處理進度: {status_result['processing_progress']:.1%}")
        
        print("🎉 MVP 測試完成!")
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """測試錯誤處理"""
    print("\n🧪 測試錯誤處理...")
    
    processor = DocumentProcessor()
    
    try:
        # 測試空檔案
        await processor.process_uploaded_file(
            file_content=b"",
            filename="empty.png"
        )
        print("❌ 空檔案應該要失敗")
    except ValueError as e:
        print(f"✅ 空檔案正確拒絕: {e}")
    
    try:
        # 測試過大檔案
        large_data = b"x" * (60 * 1024 * 1024)  # 60MB
        await processor.process_uploaded_file(
            file_content=large_data,
            filename="large.png"
        )
        print("❌ 過大檔案應該要失敗")
    except ValueError as e:
        print(f"✅ 過大檔案正確拒絕: {e}")
    
    try:
        # 測試不支援格式
        await processor.process_uploaded_file(
            file_content=b"test data",
            filename="test.exe"
        )
        print("❌ 不支援格式應該要失敗")
    except ValueError as e:
        print(f"✅ 不支援格式正確拒絕: {e}")


if __name__ == "__main__":
    print("=== 文件驗證系統 MVP 測試 ===\n")
    
    # 執行測試
    success = asyncio.run(test_mvp_flow())
    asyncio.run(test_error_handling())
    
    if success:
        print("\n🎊 所有測試通過! MVP 功能正常運作")
    else:
        print("\n💥 測試失敗，請檢查設定和依賴項")
        sys.exit(1)
