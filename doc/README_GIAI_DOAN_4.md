# Giai đoạn 4: Trực quan hóa và mô phỏng

## Mục tiêu

Trực quan cấu trúc mạng và kết quả phân tích để người xem nhận biết các node quan trọng, cụm cộng đồng và phân bố kết nối.

## Công cụ và dữ liệu

Có thể dùng Gephi để bố trí, lọc và tô màu mạng; dùng Python/NetworkX để tạo biểu đồ thống kê hoặc bản đồ. Import `data/processed/nodes.csv` dưới dạng bảng node và `data/processed/edges.csv` dưới dạng bảng edge. Chọn kiểu cạnh vô hướng và dùng `Weight` nếu muốn mã hóa độ mạnh kết nối.

Tọa độ `latitude`/`longitude` là thuộc tính node. Layout lực như ForceAtlas 2 chỉ tạo bố cục mạng, không đặt node theo tọa độ địa lý. Để mô phỏng vị trí thật cần plugin địa lý tương thích hoặc vẽ trên bản đồ bằng thư viện bản đồ.

## Hình nên chuẩn bị

- Tổng quan mạng, có lọc node cô lập hoặc thành phần nhỏ khi cần.
- Mạng tô màu theo cộng đồng, kích thước node theo centrality.
- Phân phối bậc và biểu đồ các chỉ số chính.
- Bản đồ địa lý nếu công cụ và dữ liệu tọa độ cho phép.

Lưu lại bộ lọc, cách ánh xạ màu/kích thước, chú giải và ảnh xuất để hình có thể diễn giải và tái tạo.
