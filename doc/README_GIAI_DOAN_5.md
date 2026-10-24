# Giai đoạn 5: Ứng dụng minh họa

## Tên đề tài

**Mạng lưới Ẩm thực TP.HCM: Phân tích cấu trúc địa điểm và dự đoán liên kết bằng SNA**

Tên ngắn dùng trên giao diện: **Mạng lưới Ẩm thực TP.HCM**.

## Ứng dụng

Dashboard web được viết bằng Python và Streamlit trong thư mục `web/`. Ứng dụng đọc các kết quả đã tạo ở những giai đoạn trước, không crawl dữ liệu và không tự huấn luyện lại mô hình.

### Các màn hình

- **Tổng quan:** số địa điểm, số liên kết lân cận, số thành phần liên thông, phân bố degree và biểu đồ so sánh link prediction.
- **Địa điểm & centrality:** tìm theo tên, lọc theo nhóm món, xếp hạng bằng các centrality giai đoạn 2 và xem vị trí trên bản đồ.
- **Dự đoán liên kết:** so sánh ROC-AUC/Average Precision của VGAE và ba baseline; lọc nhãn test và xem các cặp được xếp hạng cao.

Mọi kết quả được diễn giải theo đúng mô hình hiện tại: edge nghĩa là hai địa điểm cách nhau tối đa 1 km. Đây là mạng lân cận địa lý, không khẳng định quan hệ xã hội hay kinh doanh. Tab bản đồ dùng tọa độ địa điểm, còn layout/đồ thị không thể hiện đường đi thực tế.

## Cách chạy từng bước trên Windows

Ứng dụng dùng kết quả các giai đoạn trước. Trước khi chạy cần có `data/processed/centrality_scores.csv` và `link_prediction_results/link_prediction_summary.json` cùng `test_predictions.csv`.

1. Mở thư mục dự án `ggMapSNA28` trong VS Code.
2. Chọn **Terminal > New Terminal**. Terminal cần đang ở thư mục gốc, nơi nhìn thấy thư mục `web` và file `preprocess_data.py`.
3. Cài thư viện của web một lần:

```powershell
python -m pip install -r web/requirements.txt
```

4. Khởi động ứng dụng:

```powershell
python -m streamlit run web/app.py
```

5. Mở địa chỉ `http://localhost:8501` nếu trình duyệt không tự bật.
6. Khi dùng xong, quay lại Terminal và nhấn `Ctrl+C` để tắt web.

Nếu lệnh `python` không chạy, dùng `py` thay cho `python`. Nếu dự án có môi trường `.venv`, có thể kích hoạt trước khi cài thư viện:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn kích hoạt môi trường, bỏ qua bước kích hoạt; cài và chạy bằng cùng lệnh `py -m pip ...` và `py -m streamlit ...` để chúng dùng chung Python.

## Dữ liệu ứng dụng sử dụng

Dashboard tự đọc các tệp dưới đây theo đường dẫn tính từ thư mục dự án:

- `data/processed/nodes.csv`
- `data/processed/summary.json`
- `data/processed/centrality_scores.csv`
- `data/processed/centrality_summary.json`
- `link_prediction_results/link_prediction_summary.json`
- `link_prediction_results/test_predictions.csv`

Nếu thiếu file, trang sẽ liệt kê tên file chưa có. Hãy chạy script giai đoạn tương ứng trước, không cần sửa code web. Ứng dụng chỉ nạp bảng địa điểm, centrality và các cặp test; không nạp toàn bộ `edges.csv` vào bộ nhớ.

## Dùng các màn hình

- **Tổng quan:** xem số địa điểm/cạnh, biểu đồ degree và so sánh VGAE với ba baseline.
- **Địa điểm & centrality:** chọn độ đo để xếp hạng, chọn nhóm món hoặc gõ tên quán; kéo xuống dưới bảng để xem bản đồ.
- **Dự đoán liên kết:** chọn phương pháp, loại cặp và số dòng để xem các cặp địa điểm trong test.

Các centrality và điểm link prediction chỉ mô tả mạng địa điểm được nối theo khoảng cách 1 km. Chúng không khẳng định hai quán có quan hệ xã hội hoặc kinh doanh.

## Cấu trúc file

- `web/app.py`: mã nguồn dashboard.
- `web/requirements.txt`: các thư viện cần cài.

Lệnh cài đặt và chạy dashboard được ghi trong `doc/note.txt`.
