# Thêm 1 kênh / 1 tài khoản mới

Mọi bot MXH đọc danh sách tài khoản từ **một chỗ**: `E:\01_YouTube\00_Dung-chung\dang-mxh\cau-hinh.json`. Thêm tài khoản vào đó thì Gmail báo đăng, lịch đăng, đăng bù, agent kiểm 2 giờ **tự có**, không sửa code.

| Bước | Cách làm | Ai làm |
|---|---|---|
| 1. Đăng nhập tài khoản | bấm đúp `E:\01_YouTube\00_Dung-chung\social-auto-upload\2_DANG_NHAP.bat`, chọn mạng, đặt tên ngắn không dấu | Bạn |
| 2. Thêm vào máy đăng | mở Claude Code, gõ `/dang-mxh thêm tài khoản <mạng> <tên> cho kênh <kênh>` (Claude thêm khối vào `cau-hinh.json`, có `username`, tạo `cho-dang/da-dang/loi`) | Claude |
| 3. Kênh YouTube mới | bấm đúp `E:\08_AI-chung\phan-tich-mxh\ytdata\2_them_kenh.bat`, chọn kênh → agent 2 giờ tự báo "Đã đăng YouTube" + số liệu | Bạn |
| 4. Phân tích tuần | gõ `/phan-tich-mxh them <tên>` (ghi vào `E:\08_AI-chung\phan-tich-mxh\kenh.md`) | Claude |
| 5. Kiểm đồng bộ hằng giờ | thêm kênh vào `NHOM` trong `kiem-tra-mxh/kiem_dong_bo.py` | Claude |
| 6. Kiểm tra | `python he-thong-mxh\thong-bao\thong_bao_mxh.py --xem` thấy tên tài khoản mới; mở `he-thong-mxh\lich\lich-dang.html` | Claude |

Tài khoản bạn **đăng tay** (máy bật nhưng không bỏ video): thêm mã `<mang>_<cookie>` vào `DANG_TAY` trong `he-thong-mxh/chung/mxh_chung.py` để khỏi bị báo "hết video".
