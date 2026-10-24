# Giai đoạn 1: Thu thập, làm sạch và dựng đồ thị

## Mục tiêu

Gộp dữ liệu địa điểm Google Maps theo các nhóm món ăn, làm sạch những trường cần cho phân tích mạng xã hội (SNA), xác định node/edge và xuất danh sách đỉnh, danh sách cạnh cùng ma trận kề để dùng ở các giai đoạn sau.

## Mô hình mạng

- **Node (đỉnh):** một địa điểm kinh doanh. `placeId` là khóa chính; nếu thiếu, script thử lấy mã từ URL rồi mới tạo khóa dự phòng từ tên và địa chỉ.
- **Edge (cạnh):** nối hai địa điểm khác nhau nếu khoảng cách Haversine giữa tọa độ của chúng không quá 1 km. Có thể đổi ngưỡng bằng tham số `--radius-km`.
- **Đồ thị:** vô hướng, đơn, có trọng số. Quan hệ gần nhau là đối xứng nên dùng cạnh vô hướng; mỗi cặp địa điểm chỉ có một cạnh và không có self-loop.
- `distance_km` là khoảng cách địa lý, phù hợp dùng làm chi phí đường đi. `similarity_weight = 1 / distance_km` biểu diễn mức độ gần nhau.
- Ma trận kề là ma trận nhị phân đối xứng, đường chéo bằng 0, lưu dạng thưa CSR. `node_index.csv` cho biết thứ tự node tương ứng với hàng/cột.

## Làm sạch đã thực hiện

Script `preprocess_data.py` đọc các CSV trong `data/ggmap123`, chuẩn hóa Unicode và khoảng trắng, chuyển tọa độ/điểm đánh giá/số lượt đánh giá sang kiểu số, loại dòng thiếu tên hoặc có tọa độ không hợp lệ, gộp địa điểm trùng theo mã định danh, và thu thập nhãn nhóm món ăn cùng tên tệp nguồn.

Đây là bước làm sạch phục vụ phân tích mạng địa điểm, chưa phải làm sạch toàn diện mọi trường của dữ liệu gốc. Các cột không được xuất ra không bị sửa trong CSV nguồn. Việc xử lý văn bản đánh giá, phát hiện ngoại lệ dữ liệu rộng hơn, kiểm tra trùng lặp khi thiếu ID và kiểm chứng tính đại diện của dữ liệu crawl có thể thực hiện riêng nếu cần.

## Kết quả lần chạy hiện tại

Theo `summary.json` và log lần chạy có 10 tệp đầu vào:

| Chỉ số                                        | Kết quả |
| --------------------------------------------- | ------: |
| Số tệp CSV                                    |      10 |
| Số dòng đầu vào                               |  22.398 |
| Dòng bị loại do thiếu tên/tọa độ không hợp lệ |      28 |
| Bản ghi trùng được gộp sau khi loại dòng lỗi  |   2.317 |
| Số địa điểm duy nhất (node)                   |  20.053 |
| Số cạnh ở ngưỡng 1 km                         | 780.965 |
| Bậc trung bình xấp xỉ                         |   77,89 |
| Mật độ đồ thị xấp xỉ                          |  0,388% |

**Đánh giá:** số node duy nhất 20.053 đã vượt mục tiêu tối thiểu 20.000, nên có thể xem là đạt yêu cầu quy mô dữ liệu cho giai đoạn 1. Chênh lệch giữa 22.398 dòng đầu vào và 20.053 node là do 28 dòng lỗi và các địa điểm trùng được gộp; không nên so trực tiếp số node với tổng số dòng crawl.

Thống kê crawl ban đầu là 20.379 dòng; sau khi thêm khoảng 2.000 dòng dự kiến 22.379, trong khi script đếm được 22.398. Có chênh lệch 19 dòng so với số tổng hợp thủ công; nên đối chiếu số dòng thực tế từng CSV nếu cần báo cáo chính xác theo nguồn. Dù vậy, số node duy nhất sau làm sạch được script ghi nhận rõ và đã trên 20.000.

780.965 cạnh là con số lớn để hiển thị, nhưng mật độ khoảng 0,388% cho thấy đồ thị vẫn thưa so với số cạnh tối đa có thể có. Mỗi node có trung bình khoảng 77,89 láng giềng trong ngưỡng 1 km. Kết quả phụ thuộc mạnh vào bán kính: tăng bán kính sẽ làm số cạnh tăng nhanh. Nên xem 1 km là tham số mô hình cần giải thích và có thể so sánh thêm một vài ngưỡng trong phân tích độ nhạy; đây không phải quan hệ xã hội quan sát trực tiếp, mà là mạng lân cận địa lý được định nghĩa từ dữ liệu.

## Tệp đầu ra

Thư mục mặc định: `data/processed/`.

- `nodes.csv`: node và thuộc tính địa điểm. Có các trường `Id` và `Label` phục vụ nhập Gephi, cùng `node_id`, `place_id`, tên, địa chỉ, danh mục, tọa độ, rating và số lượt đánh giá.
- `edges.csv`: cạnh với các trường Gephi `Source`, `Target`, `Type`, `Weight`; đồng thời giữ `distance_km` và `similarity_weight`.
- `restaurants_network.gexf`: toàn bộ đồ thị trong một tệp, gồm node, edge, nhãn, thuộc tính và trọng số; đây là tệp nên dùng để mở trực tiếp trong Gephi.
- `node_index.csv`: ánh xạ chỉ số 0-based của ma trận sang `node_id`.
- `adjacency_matrix.npz`: ma trận kề thưa SciPy CSR; không phải CSV thông thường.
- `summary.json`: thống kê làm sạch và mô tả đồ thị.

## Mở trên Gephi

Chạy lại `py preprocess_data.py` sau khi cập nhật script. Mở Gephi, chọn **File > Open**, chọn `data/processed/restaurants_network.gexf`, rồi chấp nhận hộp thoại import mặc định. Tệp đã khai báo mạng vô hướng và chứa sẵn node, edge, nhãn, thuộc tính cùng trọng số; không cần tự nhập/ghép hai CSV. Sau khi đồ thị nạp xong, mở tab **Overview** và bấm **Run** ở mục **Layout** để bố trí mạng (có thể chọn ForceAtlas 2).

Hai CSV `nodes.csv` và `edges.csv` vẫn được giữ để kiểm tra hoặc dùng ở công cụ khác; nếu dùng Gephi thì ưu tiên tệp GEXF duy nhất ở trên.

Với khoảng 20 nghìn node và 781 nghìn cạnh, Gephi có thể mở mạng này, nhưng cần bộ nhớ đủ và layout có thể mất thời gian. Nếu máy yếu, thử lọc thành phần liên thông hoặc giảm bán kính/giới hạn dữ liệu trong một bản thử riêng. `latitude` và `longitude` sẽ được nhập như thuộc tính; layout ForceAtlas 2 không tự đặt node lên bản đồ địa lý. Muốn hiển thị đúng vị trí trên bản đồ cần plugin/layout địa lý tương thích hoặc công cụ GIS.

Không dùng `similarity_weight` làm chi phí shortest path: trọng số này càng lớn khi hai node càng gần. Với đường đi địa lý, dùng `distance_km`. Ma trận kề hiện tại chỉ mã hóa có/không có cạnh (0/1).

## Lệnh chạy

Các lệnh được giữ riêng trong `doc/note.txt`.
