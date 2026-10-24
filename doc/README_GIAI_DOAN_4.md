# Giai đoạn 4: Trực quan hóa và mô phỏng

## Mục tiêu

Trực quan hóa kết quả link prediction giai đoạn 3 trong Gephi: các cặp node được mô hình xếp hạng cao, nhãn thực tế của cặp test và điểm của VGAE cùng các baseline.

## Tạo file Gephi

Từ thư mục gốc dự án, chạy:

```powershell
py export_link_prediction_gephi.py --processed-dir data/processed --results-dir link_prediction_results --top-k 500
```

Script tạo `link_prediction_results/link_prediction_gephi.gexf`. Mặc định chọn 500 cặp có điểm cao nhất và 500 cặp có điểm thấp nhất theo từng phương pháp VGAE, Common Neighbors, Jaccard và Adamic–Adar; nếu một cặp được nhiều phương pháp chọn thì chỉ xuất một lần. File có tối đa 4.000 cạnh và chỉ chứa node xuất hiện trong các cạnh đã chọn, giúp dễ xem hơn toàn bộ mạng 20 nghìn node.

Với kết quả hiện tại, file có 2.303 cạnh duy nhất (1.308 test positive, 995 sampled negative) và 2.451 node. Số lượng sẽ thay đổi nếu file dự đoán hoặc tham số `--top-k` thay đổi.

Nếu kết quả giai đoạn 3 đang ở thư mục Kaggle, tải `test_predictions.csv` về `link_prediction_results/` trong dự án trước khi chạy lệnh. Script đọc node và thuộc tính từ `data/processed/nodes.csv`, đồng thời tự thêm các chỉ số centrality nếu thấy `data/processed/centrality_scores.csv`.

## Mở trong Gephi cho người mới

1. Chạy lệnh tạo file ở trên trong PowerShell tại thư mục gốc dự án.
2. Mở Gephi, chọn **File > Open**.
3. Mở file `link_prediction_results/link_prediction_gephi.gexf`.
4. Nếu hiện hộp thoại Import, chọn **Undirected** nếu được hỏi và bấm **OK**.
5. Chuyển sang tab **Overview**. Ở khung **Layout**, chọn **ForceAtlas 2**, bấm **Run**; khi các node đã dàn ra, bấm **Stop**.
6. Trong **Appearance**, chọn áp dụng cho **Edges**, tô màu theo thuộc tính `test_label`: `1` là cạnh test thật bị giữ lại, `0` là cặp âm được lấy mẫu. Nếu giao diện phiên bản Gephi không cho tô theo thuộc tính, mở **Data Laboratory > Edges** để xem các cột `test_label` và `selected_by`.
7. Có thể tô màu node theo `food_categories`, hoặc chỉnh kích thước node theo `degree` nếu thuộc tính này có trong dữ liệu.
8. Lưu project bằng **File > Save As** nếu muốn giữ bố cục; xuất hình bằng **Preview > Refresh > Export: SVG/PDF/PNG**.
   (Trong Gephi, ở Overview, mở bảng Appearance rồi chọn:

Edges để chỉnh cạnh; chọn Ranking, chọn test_label, rồi chọn thang màu. 0 là cặp âm được lấy mẫu, 1 là cạnh thật bị giấu khỏi train. Vì vậy cạnh sẽ đổi màu để phân biệt hai loại.
Nodes để chỉnh node; chọn Partition và food_categories để tô các nhóm món khác màu nhau, hoặc chọn Ranking và degree để node có nhiều hàng xóm hiện lớn hơn.)

## Cách đọc hình

- `test_label = 1`: liên kết có thật trong tập test nhưng đã bị ẩn khỏi đồ thị huấn luyện.
- `test_label = 0`: cặp không có cạnh trong dữ liệu quan sát, được dùng làm negative sample.
- `selected_by`: phương pháp và phía xếp hạng đã chọn cạnh, ví dụ `VGAE:top` hoặc `Jaccard:bottom`.
- `vgae_score`, `common_neighbors`, `jaccard`, `adamic_adar`: điểm từng phương pháp cho cùng cặp.

Đây là đồ thị gồm các **cặp ứng viên test ở hai đầu bảng xếp hạng** (điểm cao và điểm thấp), không phải đồ thị đầy đủ của tất cả 780.965 cạnh. Cặp âm chỉ là negative sample, không chứng minh hai địa điểm không có quan hệ ngoài đời. Do baseline đạt điểm cao hơn VGAE trong thí nghiệm hiện tại, hình có thể giúp so sánh các cặp được các phương pháp chọn, nhưng không nên trình bày như VGAE dự đoán tốt nhất.

Tọa độ `latitude`/`longitude` và các centrality được đưa vào như thuộc tính node; layout ForceAtlas 2 tạo bố cục mạng, không định vị địa lý thật.
