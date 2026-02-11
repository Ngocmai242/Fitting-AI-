import sys
sys.path.insert(0, 'data_engine/crawler')
from shopee import ShopeeCrawler

# Test categorization
crawler = ShopeeCrawler()

test_names = [
    "Áo khoác dạ bomber dáng ngắn basic khóa kéo áo khoác dạ ép 2 lớp tay bồng ấm áp A60 SUTANO",
    "Quần jean ống rộng nữ form rộng lưng cao",
    "Chân váy midi xòe công sở nữ",
    "Giày sneaker thể thao nam"
]

print("=" * 80)
print("TEST HỆ THỐNG PHÂN LOẠI CHI TIẾT")
print("=" * 80)

for name in test_names:
    print(f"\nSản phẩm: {name}")
    print("-" * 80)
    result = crawler.determine_detailed_category(name)
    for key, value in result.items():
        print(f"  {key:15}: {value}")
