# Giai đoạn 3: Lựa chọn và áp dụng thuật toán

## Mục tiêu

Chọn thuật toán phù hợp với câu hỏi nghiên cứu và loại mạng, thực hiện trên đồ thị địa điểm đã chuẩn hóa, sau đó đánh giá kết quả bằng tiêu chí rõ ràng.

## Hướng lựa chọn

Có thể chọn phát hiện cộng đồng (ví dụ Louvain/Leiden nếu thư viện phù hợp), xếp hạng node theo centrality, hoặc một bài toán dự đoán/phân loại nếu có nhãn mục tiêu đủ tin cậy. Không nên chọn thuật toán chỉ vì dễ chạy; cần nêu câu hỏi, đầu vào, giả định, tham số và cách đánh giá.

Với dữ liệu hiện tại, phát hiện cộng đồng trên mạng lân cận địa lý là hướng khả thi để khảo sát các cụm địa điểm gần nhau. Cộng đồng phản ánh cấu trúc của mạng đã định nghĩa theo bán kính 1 km, không tự động đồng nghĩa với khu vực hành chính hay nhóm kinh doanh có liên kết thực tế.

## Thiết kế thực nghiệm

- Ghi lại phiên bản thư viện và cấu hình thuật toán.
- So sánh độ ổn định khi thay đổi bán kính hoặc tham số chính.
- Dùng modularity và kiểm tra định tính trên bản đồ/bảng thuộc tính khi phù hợp.
- Báo cáo giới hạn dữ liệu crawl, địa bàn, độ phủ và sai số định vị.

Mô tả thuật toán cuối cùng và lệnh thực thi tại đây sau khi chốt câu hỏi nghiên cứu.
