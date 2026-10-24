# Giai đoạn 2: Phân tích mạng xã hội

## Mục tiêu

Tính Degree, Betweenness, Closeness, Harmonic, Eigenvector, Katz, PageRank và HITS trên đồ thị giai đoạn 1 để so sánh các cách định nghĩa mức độ trung tâm của địa điểm.

## Dữ liệu đầu vào

Dùng `data/processed/nodes.csv` và `data/processed/edges.csv` làm nguồn chính. `adjacency_matrix.npz` là ma trận kề nhị phân CSR; thứ tự node trong ma trận được ánh xạ bởi `node_index.csv`. Đồ thị hiện là vô hướng và edge biểu thị hai địa điểm trong bán kính 1 km.

## Chạy script

Tại thư mục gốc dự án, cài NetworkX nếu chưa có rồi chạy:

```powershell
py -m pip install networkx
py compute_centrality.py
```

Mặc định script đọc `data/processed/nodes.csv` và `data/processed/edges.csv`, ghi `centrality_scores.csv` và `centrality_summary.json` vào `data/processed/`. Muốn thay số nguồn lấy mẫu hoặc cố định seed khác:

```powershell
py compute_centrality.py --samples 1000 --seed 42
```

Lệnh chạy cũng được ghi trong `doc/note.txt`. Script chỉ đọc dữ liệu đã xử lý và không sửa các file đầu vào.

## Các độ đo và cách đọc

- `degree`: số láng giềng thực tế; `degree_centrality`: degree chuẩn hóa theo số node.
- `betweenness_approx`: ước lượng Betweenness bằng lấy mẫu nguồn theo NetworkX.
- `closeness_approx`: ước lượng Closeness từ các nguồn lấy mẫu, có hiệu chỉnh reachability khi đồ thị không liên thông.
- `harmonic_centrality_approx`: ước lượng Harmonic, node không tới được đóng góp 0.
- `eigenvector_centrality`: điểm cao khi kết nối với các node cũng có điểm cao.
- `katz_centrality`: tính ảnh hưởng của các walk có độ dài khác nhau với hệ số giảm; alpha được đặt bảo thủ theo bậc cực đại.
- `pagerank`: xác suất ổn định với damping 0,85; trên mạng vô hướng, mỗi cạnh được xem như hai chiều.
- `hits_hub`, `hits_authority`: có xuất riêng nhưng HITS trên mạng vô hướng suy biến và hai điểm không mang ý nghĩa hub/authority như trên mạng có hướng; diễn giải thận trọng.

Đồ thị có quy mô lớn nên Betweenness, Closeness và Harmonic dùng 500 nguồn mẫu mặc định, seed 42 để tái lập. Đây là kết quả xấp xỉ, không phải phép tính exact trên mọi nguồn. Có thể tăng `--samples` để giảm sai số nhưng thời gian chạy tăng tương ứng. Số nguồn đã dùng và các thông tin cấu hình được ghi trong `centrality_summary.json`.

`centrality_scores.csv` có một dòng mỗi node. Để mô tả kết quả, sắp xếp giảm dần theo từng cột centrality và kiểm tra top node; không so trực tiếp độ lớn giữa các thước đo khác định nghĩa.

## Diễn giải kết quả

### Kết quả lần chạy hiện tại

Script chạy thành công, `errors` rỗng; đã đọc đủ 20.053 node và 780.965 cạnh, không bỏ cạnh nào và không có self-loop. Đồ thị có 373 thành phần liên thông; thành phần lớn nhất gồm 12.100 node (xấp xỉ 60,3%). Mật độ là 0,003884 (xấp xỉ 0,3884%) và bậc trung bình là 77,89.

Một số node đứng đầu theo từng chỉ số trong `centrality_scores.csv`:

| Độ đo                | Node đứng đầu trong lần chạy                                       |                Điểm |
| -------------------- | ------------------------------------------------------------------ | ------------------: |
| Degree               | Quán Bún Thái                                                      |      619 láng giềng |
| Betweenness (xấp xỉ) | TIỆM NƯỚNG NÀNG PHƯƠNG - QUÁN NƯỚNG NGON HÓC MÔN - LẨU SỮA HÓC MÔN |             0,06351 |
| Closeness (xấp xỉ)   | Bánh canh cua Ohh Mê Ly                                            |             0,03123 |
| Harmonic (xấp xỉ)    | Tiệm Bánh Mặt Trời                                                 |             0,06604 |
| Eigenvector          | Quán Bún Thái                                                      |             0,05216 |
| Katz                 | Quán Bún Thái                                                      |             0,02086 |
| PageRank             | Công Ty TNHH Thực Phẩm Chay Thịnh Phát                             |          0,00009345 |
| HITS hub / authority | Quán Bún Thái                                                      | 0,001817 cho cả hai |

Degree, Eigenvector và Katz cùng xếp Quán Bún Thái đầu bảng; điều này cho thấy node này vừa có nhiều láng giềng vừa nằm trong vùng có kết nối mạnh theo các thước đo phổ. Các thước đo khác chọn node khác nhau vì chúng phản ánh khía cạnh khác: Betweenness thiên về vai trò trung gian, còn Closeness/Harmonic xét khoảng cách tới các node khác. Đây là thứ hạng của lần chạy hiện tại, không phải kết luận về chất lượng hay tầm quan trọng kinh doanh.

Betweenness, Closeness và Harmonic dùng 500 nguồn lấy mẫu với seed 42 nên thứ hạng/điểm là xấp xỉ và có thể thay đổi khi đổi số mẫu. HITS hub và authority bằng nhau trên mạng vô hướng, vì vậy không cung cấp hai cách xếp hạng độc lập và chỉ nên báo cáo như giới hạn phương pháp. Với 373 thành phần liên thông, diễn giải Closeness cần thận trọng; Harmonic phù hợp hơn để phản ánh các node không thể đi tới nhau. Eigenvector trên đồ thị không liên thông cũng cần xem xét theo thành phần, không nên mặc định so sánh như thể mạng liên thông duy nhất.

Các chỉ số mô tả mạng lân cận địa lý: một cạnh biểu thị hai địa điểm cách nhau tối đa 1 km. Vì vậy, “trung tâm” ở đây có nghĩa theo cấu trúc mạng được dựng, không khẳng định quan hệ xã hội hoặc mức độ nổi tiếng ngoài đời.

## Lưu ý phương pháp

Các centrality trong script dùng đồ thị vô hướng, không trọng số: một cạnh tương đương một bước đi. Không dùng `similarity_weight` làm khoảng cách. Vì HITS vốn phù hợp với mạng có hướng, điểm HITS trên đồ thị này chỉ được xuất để đối chiếu công thức, không nên xem là kết quả hub/authority có diễn giải mạnh.
