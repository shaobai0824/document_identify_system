import asyncio
from datetime import datetime
from typing import AsyncGenerator, Tuple


async def _generate_watermarked_content(original_content: AsyncGenerator[bytes, None], watermark_text: str) -> AsyncGenerator[bytes, None]:
    # 這裡應該有實際的浮水印邏輯，例如使用 img2pdf 或 reportlab
    # 由於是模擬，我們只是將浮水印文字附加到內容中
    print(f"模擬添加浮水印: {watermark_text}")
    async for chunk in original_content:
        yield chunk
    yield f"\n--- Watermarked by {watermark_text} at {datetime.utcnow().isoformat()} ---".encode('utf-8')
    await asyncio.sleep(0.01) # 模擬異步處理延遲

class WatermarkService:
    async def apply_watermark(
        self,
        document_id: str,
        user_info: str,
        download_time: datetime,
        reason: str
    ) -> Tuple[AsyncGenerator[bytes, None], str]:
        # 實際應用浮水印的邏輯
        print(f"模擬為文件 {document_id} 應用浮水印. 用戶: {user_info}, 時間: {download_time}, 原因: {reason}")

        # 假設從 StorageService 獲取原始文件內容
        from .storage_service import StorageService  # 避免循環導入
        storage_service = StorageService()
        original_file_stream, media_type = await storage_service.get_document(document_id)

        watermark_text = f"Confidential - {user_info}"
        watermarked_stream = _generate_watermarked_content(original_file_stream, watermark_text)
        return watermarked_stream, media_type
