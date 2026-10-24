# Giai đoạn 2: Phân tích mạng xã hội

## Mục tiêu

Tính các chỉ số cấu trúc trên đồ thị đã tạo ở giai đoạn 1 để mô tả mức độ kết nối, vai trò của từng địa điểm và cấu trúc cộng đồng.

## Dữ liệu đầu vào

Dùng `data/processed/nodes.csv` và `data/processed/edges.csv` làm nguồn chính. `adjacency_matrix.npz` là ma trận kề nhị phân CSR; thứ tự node trong ma trận được ánh xạ bởi `node_index.csv`. Đồ thị hiện là vô hướng và edge biểu thị hai địa điểm trong bán kính 1 km.

## Chỉ số có thể phân tích

- Degree và phân phối bậc: số địa điểm lân cận của mỗi node.
- Betweenness centrality: mức độ một node nằm trên các đường đi ngắn nhất.
- Closeness centrality và shortest-path length: khoảng cách đến các node khác; cần xử lý riêng các thành phần liên thông.
- Clustering coefficient: mức độ các láng giềng của một node cũng kết nối với nhau.
- Density và diameter: tính trên toàn đồ thị liên thông hoặc báo cáo theo thành phần; không diễn giải diameter toàn cục khi mạng không liên thông.
- Eigenvector centrality và HITS: mức ảnh hưởng theo cấu trúc kết nối; cần kiểm tra hội tụ và cách định nghĩa trọng số.
- Modularity/community detection: phân cụm cấu trúc; cần nêu thuật toán và tham số.

## Lưu ý phương pháp

Đồ thị có 20.053 node và 780.965 cạnh ở bán kính 1 km. Betweenness chính xác trên toàn mạng có thể tốn thời gian; cân nhắc thuật toán xấp xỉ, lấy mẫu hoặc phân tích theo thành phần liên thông. Phân biệt rõ `distance_km` (chi phí đường đi) với `similarity_weight` (độ mạnh kết nối); không dùng trọng số tương đồng như chi phí shortest path. Các chỉ số trên mô tả mạng lân cận địa lý được xây dựng, không phải quan hệ xã hội quan sát trực tiếp.

## Đầu ra dự kiến

Tạo bảng CSV các chỉ số theo node, thống kê tổng thể và thông tin cấu hình/thuật toán để kết quả có thể tái lập. Lệnh chạy được ghi trong `doc/note.txt` khi script giai đoạn 2 sẵn sàng.
