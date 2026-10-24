# Giai đoạn 3: Dự đoán liên kết bằng VGAE

## Câu hỏi nghiên cứu

Biểu diễn node học từ cấu trúc mạng có dự đoán các cạnh bị ẩn tốt hơn những độ đo cấu trúc truyền thống hay không?

## Thuật toán được chọn

Dùng **Variational Graph Autoencoder (VGAE)** với encoder GCN hai lớp và decoder tích vô hướng. Đây là một thuật toán trong nhóm của topic 2 đề xuất, không cài thêm Node2Vec hoặc GAE riêng.

Để có đối chứng, script đồng thời chấm ba baseline truyền thống: Common Neighbors (CN), Jaccard và Adamic–Adar. Đây không phải các thuật toán học thêm; chúng là các độ đo cấu trúc dùng làm mốc so sánh cho VGAE.

## Thiết kế đánh giá

- Đồ thị đầu vào là đồ thị vô hướng, mỗi cạnh biểu thị hai địa điểm cách nhau không quá 1 km.
- Chia ngẫu nhiên cạnh dương thành 80% train, 10% validation, 10% test (seed mặc định 42). Các cạnh validation/test bị loại khỏi đồ thị encoder trong lúc huấn luyện.
- Cặp âm được lấy từ các cặp node không có cạnh trong toàn bộ đồ thị quan sát; vì vậy không lấy nhầm cạnh validation/test làm nhãn âm.
- Các phương pháp được đánh giá trên cùng tập cạnh test dương và âm bằng ROC-AUC và Average Precision.
- VGAE chọn checkpoint theo ROC-AUC validation, có early stopping. Mặc định tối đa 100 epoch, 200.000 cạnh dương train mỗi epoch, hidden size 64, latent size 32.

Đây là thí nghiệm dự đoán cạnh bị ẩn trong **mạng lân cận địa lý**, không phải dự đoán một quan hệ xã hội/kinh doanh trong tương lai. Việc lấy mẫu âm cân bằng 1:1 thuận lợi để so thứ hạng bằng ROC-AUC; Average Precision trong thiết lập này không đại diện cho tỷ lệ cạnh thật ngoài đời.

## Đưa dữ liệu và script lên Kaggle

Tạo một Kaggle Dataset chứa:

- `link_prediction_vgae.py`
- thư mục `processed/` gồm `nodes.csv` và `edges.csv` từ `data/processed/`

Có thể giữ các file khác nhưng script chỉ cần hai CSV trên. Trong Kaggle Notebook, chọn **Add Data** để đính kèm dataset vừa tạo, sau đó vào **Notebook options > Accelerator > GPU**. Chạy cell sau; cell tự tìm script và cặp CSV trong `/kaggle/input`, rồi ghi kết quả ở `/kaggle/working/link_prediction_results`:

```python
from pathlib import Path
import subprocess
import sys
import torch

assert torch.cuda.is_available(), "Hãy bật GPU trong Notebook options > Accelerator"

kaggle_input = Path("/kaggle/input")
script = next(kaggle_input.rglob("link_prediction_vgae.py"), None)
edges_file = next(kaggle_input.rglob("edges.csv"), None)
if script is None or edges_file is None:
    raise FileNotFoundError(
        "Dataset cần chứa link_prediction_vgae.py và processed/edges.csv"
    )
processed_dir = edges_file.parent
if not (processed_dir / "nodes.csv").is_file():
    raise FileNotFoundError(f"Thiếu nodes.csv trong {processed_dir}")

output_dir = Path("/kaggle/working/link_prediction_results")
command = [
    sys.executable,
    str(script),
    "--input-dir", str(processed_dir),
    "--output-dir", str(output_dir),
    "--device", "cuda",
    "--epochs", "100",
]
subprocess.run(command, check=True)
print("Kết quả:", output_dir)
```

## Chạy trên máy cá nhân (tùy chọn)

Cần Python, PyTorch, NumPy, SciPy và scikit-learn. Mặc định thiết bị là `auto`, tức dùng CUDA nếu khả dụng, nếu không thì CPU:

```powershell
py -m pip install torch numpy scipy scikit-learn
py link_prediction_vgae.py --input-dir data/processed --output-dir link_prediction_results --device auto
```

## Đầu ra

- `link_prediction_summary.json`: cấu hình chia tập, thiết bị/ GPU, epoch tốt nhất và ROC-AUC/Average Precision test của VGAE, CN, Jaccard, Adamic–Adar.
- `test_predictions.csv`: nhãn thật và điểm dự đoán từng cặp test của bốn phương pháp.

## Kết quả lần chạy Kaggle

Thí nghiệm chạy trên GPU Tesla T4 với 20.053 node và 780.965 cạnh. Chia dữ liệu gồm 624.773 cạnh train, 78.096 validation và 78.096 test; tập test có thêm 78.096 cặp âm. VGAE dừng sớm tại epoch 36 và chọn checkpoint tốt nhất ở epoch 24, đạt validation ROC-AUC 0,86483. Thời gian chạy được ghi nhận là 20,59 giây.

| Phương pháp      | Test ROC-AUC | Test Average Precision |
| ---------------- | -----------: | ---------------------: |
| Common Neighbors |      0,99870 |                0,99825 |
| Jaccard          |  **0,99952** |            **0,99950** |
| Adamic–Adar      |      0,99890 |                0,99857 |
| VGAE             |      0,86493 |                0,86384 |

### Nhận xét

Trong thiết lập thử nghiệm này, câu trả lời là **không**: VGAE không cải thiện khả năng dự đoán cạnh bị ẩn so với các độ đo cấu trúc truyền thống. Jaccard tốt nhất trên cả hai chỉ số; ROC-AUC của VGAE thấp hơn Jaccard khoảng 0,13459 và Average Precision thấp hơn khoảng 0,13566. Kết quả cho thấy với mạng lân cận địa lý này, các láng giềng chung đã cung cấp tín hiệu rất mạnh, còn embedding VGAE hiện tại chưa học được biểu diễn hữu ích bằng các baseline đơn giản.

Đây là kết luận cho một lần chia ngẫu nhiên duy nhất (seed 42), không phải bằng chứng rằng mọi cấu hình VGAE đều kém hơn. Negative được lấy ngẫu nhiên đồng đều từ tất cả cặp không có cạnh; do đồ thị được tạo theo khoảng cách, nhiều negative ở xa và dễ phân biệt với positive gần nhau. Điều này có thể làm các baseline địa phương đạt điểm gần 1.0. Nếu muốn kiểm tra khó và sát hơn, thí nghiệm tiếp theo nên dùng **hard negatives** được ghép theo khoảng cách địa lý/khu vực với positive, hoặc lặp nhiều seed và báo cáo trung bình cùng độ lệch chuẩn.

Chỉ số Average Precision được tính trên test cân bằng 1:1 (78.096 positive và 78.096 negative), nên không đại diện cho tỷ lệ liên kết thật trong toàn bộ các cặp địa điểm. Bài toán hiện tại dự đoán cạnh bị ẩn trong mạng khoảng cách 1 km, không phải dự đoán quan hệ xã hội/kinh doanh trong tương lai.

### Cảnh báo khi chạy

PyTorch phát cảnh báo sparse invariant checks đang tắt khi tạo sparse COO tensor. Đây là cảnh báo hiệu năng/kiểm tra, không làm lần chạy thất bại; log cho thấy huấn luyện và chấm điểm hoàn tất. Nếu muốn loại cảnh báo ở lần sau, có thể bật kiểm tra invariant, nhưng có thể tăng thời gian tạo tensor.

Kết quả chi tiết nằm trong `link_prediction_results/link_prediction_summary.json`; dự đoán từng cặp test nằm trong `test_predictions.csv`.
