import json
import time
import re
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

class ShopeeCrawler:
    def __init__(self):
        self.products = []
        self.shop_id = None

    def preprocess_name(self, name):
        """Tiền xử lý tên sản phẩm: lowercase, xóa emoji và ký tự đặc biệt"""
        # Chuyển thường
        name = name.lower()
        # Xóa emoji và ký tự đặc biệt phổ biến trên Shopee
        name = re.sub(r'[🔥🚀⚡💥✨🎉🎊🎁💝💖💕❤️⭐🌟]', '', name)
        name = re.sub(r'[\[\]\(\){}]', ' ', name)
        # Giữ lại chữ, số, khoảng trắng và các ký tự tiếng Việt
        name = re.sub(r'[^\w\sàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ-]', ' ', name)
        # Xóa khoảng trắng thừa
        name = ' '.join(name.split())
        return name

    def determine_detailed_category(self, name):
        """Phân loại chi tiết sản phẩm theo nhiều thuộc tính"""
        name_clean = self.preprocess_name(name)
        
        # === LOẠI SẢN PHẨM ===
        # Ưu tiên từ cụ thể đến tổng quát (specific to general)
        product_type = "Uncategorized"
        sub_category = "General"
        
        # === ÁO (TOPS) - Từ cụ thể đến tổng quát ===
        
        # Áo khoác
        if any(kw in name_clean for kw in ['áo khoác dạ', 'áo dạ', 'coat dạ']):
            product_type, sub_category = "top", "Áo khoác dạ"
        elif any(kw in name_clean for kw in ['áo khoác bomber', 'bomber jacket', 'áo bomber']):
            product_type, sub_category = "top", "Áo khoác bomber"
        elif any(kw in name_clean for kw in ['áo khoác gió', 'áo gió', 'windbreaker']):
            product_type, sub_category = "top", "Áo khoác gió"
        elif any(kw in name_clean for kw in ['áo khoác jean', 'áo khoác bò', 'denim jacket']):
            product_type, sub_category = "top", "Áo khoác jean"
        elif any(kw in name_clean for kw in ['áo khoác da', 'leather jacket']):
            product_type, sub_category = "top", "Áo khoác da"
        elif any(kw in name_clean for kw in ['blazer', 'vest khoác']):
            product_type, sub_category = "top", "Áo blazer"
        elif any(kw in name_clean for kw in ['cardigan', 'áo cardigan']):
            product_type, sub_category = "top", "Áo cardigan"
        elif any(kw in name_clean for kw in ['áo khoác', 'jacket', 'coat']):
            product_type, sub_category = "top", "Áo khoác"
        
        # Áo len/nỉ
        elif any(kw in name_clean for kw in ['hoodie', 'áo hoodie']):
            product_type, sub_category = "top", "Áo hoodie"
        elif any(kw in name_clean for kw in ['áo nỉ', 'sweater', 'sweatshirt']):
            product_type, sub_category = "top", "Áo nỉ"
        elif any(kw in name_clean for kw in ['áo len', 'áo dệt kim', 'knitwear']):
            product_type, sub_category = "top", "Áo len"
        
        # Áo sơ mi
        elif any(kw in name_clean for kw in ['áo sơ mi tay dài', 'sơ mi dài tay']):
            product_type, sub_category = "top", "Áo sơ mi tay dài"
        elif any(kw in name_clean for kw in ['áo sơ mi tay ngắn', 'sơ mi ngắn tay']):
            product_type, sub_category = "top", "Áo sơ mi tay ngắn"
        elif any(kw in name_clean for kw in ['áo sơ mi', 'sơ mi', 'shirt']):
            product_type, sub_category = "top", "Áo sơ mi"
        
        # Áo thun
        elif any(kw in name_clean for kw in ['áo thun form rộng', 'áo phông oversiz', 'áo thun oversiz']):
            product_type, sub_category = "top", "Áo thun form rộng"
        elif any(kw in name_clean for kw in ['áo thun tay dài', 'áo phông tay dài']):
            product_type, sub_category = "top", "Áo thun tay dài"
        elif any(kw in name_clean for kw in ['áo thun', 't-shirt', 'tshirt', 'áo phông']):
            product_type, sub_category = "top", "Áo thun"
        
        # Áo polo
        elif any(kw in name_clean for kw in ['áo polo', 'polo shirt']):
            product_type, sub_category = "top", "Áo polo"
        
        # Áo kiểu/blouse
        elif any(kw in name_clean for kw in ['áo babydoll', 'babydoll']):
            product_type, sub_category = "top", "Áo babydoll"
        elif any(kw in name_clean for kw in ['áo kiểu', 'blouse', 'áo công sở nữ']):
            product_type, sub_category = "top", "Áo kiểu"
        
        # Áo 2 dây/tank top/croptop
        elif any(kw in name_clean for kw in ['croptop', 'crop top', 'áo crop']):
            product_type, sub_category = "top", "Áo croptop"
        elif any(kw in name_clean for kw in ['áo 2 dây', 'áo hai dây', 'camisole']):
            product_type, sub_category = "top", "Áo 2 dây"
        elif any(kw in name_clean for kw in ['áo ba lỗ', 'áo tank', 'tanktop', 'tank top']):
            product_type, sub_category = "top", "Áo ba lỗ"
        
        # Áo lót
        elif any(kw in name_clean for kw in ['áo lót', 'áo bra', 'áo ngực', 'bra']):
            product_type, sub_category = "top", "Áo lót"
        
        # Áo dài
        elif any(kw in name_clean for kw in ['áo dài']):
            product_type, sub_category = "top", "Áo dài"
        
        # Tổng quát
        elif any(kw in name_clean for kw in ['áo', 'top']):
            product_type, sub_category = "top", "Áo"
        
        # === QUẦN (BOTTOMS) - Từ cụ thể đến tổng quát ===
        
        # Quần Jean
        elif any(kw in name_clean for kw in ['quần jean ống rộng', 'quần bò ống rộng', 'jeans rộng']):
            product_type, sub_category = "bottom", "Quần jean ống rộng"
        elif any(kw in name_clean for kw in ['quần jean ống đứng', 'quần bò ống đứng']):
            product_type, sub_category = "bottom", "Quần jean ống đứng"
        elif any(kw in name_clean for kw in ['quần jean ống loe', 'quần bò ống loe', 'quần jean loe', 'flare jeans']):
            product_type, sub_category = "bottom", "Quần jean ống loe"
        elif any(kw in name_clean for kw in ['quần jean baggy', 'quần bò baggy', 'baggy jeans']):
            product_type, sub_category = "bottom", "Quần jean baggy"
        elif any(kw in name_clean for kw in ['quần jean skinny', 'quần bò ôm', 'skinny jeans']):
            product_type, sub_category = "bottom", "Quần jean skinny"
        elif any(kw in name_clean for kw in ['quần jean rách', 'quần bò rách', 'ripped jeans']):
            product_type, sub_category = "bottom", "Quần jean rách"
        elif any(kw in name_clean for kw in ['quần jean', 'quần jeans', 'quần bò', 'denim pants']):
            product_type, sub_category = "bottom", "Quần jean"
        
        # Quần tây/âu/vải
        elif any(kw in name_clean for kw in ['quần tây ống rộng', 'quần âu rộng']):
            product_type, sub_category = "bottom", "Quần tây ống rộng"
        elif any(kw in name_clean for kw in ['quần tây ống đứng', 'quần âu ống đứng']):
            product_type, sub_category = "bottom", "Quần tây ống đứng"
        elif any(kw in name_clean for kw in ['quần tây', 'quần âu', 'quần vải', 'dress pants', 'trousers']):
            product_type, sub_category = "bottom", "Quần tây"
        
        # Quần short/đùi
        elif any(kw in name_clean for kw in ['quần short jean', 'quần đùi jean', 'quần soóc jean']):
            product_type, sub_category = "bottom", "Quần short jean"
        elif any(kw in name_clean for kw in ['quần short kaki', 'quần đùi kaki']):
            product_type, sub_category = "bottom", "Quần short kaki"
        elif any(kw in name_clean for kw in ['quần short', 'quần đùi', 'quần soóc', 'shorts']):
            product_type, sub_category = "bottom", "Quần short"
        
        # Quần dài khác
        elif any(kw in name_clean for kw in ['quần culottes', 'culottes']):
            product_type, sub_category = "bottom", "Quần culottes"
        elif any(kw in name_clean for kw in ['quần ống rộng', 'quần suông', 'wide leg pants']):
            product_type, sub_category = "bottom", "Quần ống rộng"
        elif any(kw in name_clean for kw in ['quần ống côn', 'quần côn']):
            product_type, sub_category = "bottom", "Quần ống côn"
        elif any(kw in name_clean for kw in ['quần baggy', 'baggy pants']):
            product_type, sub_category = "bottom", "Quần baggy"
        elif any(kw in name_clean for kw in ['quần jogger', 'jogger pants']):
            product_type, sub_category = "bottom", "Quần jogger"
        elif any(kw in name_clean for kw in ['quần kaki', 'kaki pants']):
            product_type, sub_category = "bottom", "Quần kaki"
        elif any(kw in name_clean for kw in ['quần legging', 'legging', 'quần tất dài']):
            product_type, sub_category = "bottom", "Quần legging"
        elif any(kw in name_clean for kw in ['quần thể thao', 'quần tập', 'sport pants', 'gym pants']):
            product_type, sub_category = "bottom", "Quần thể thao"
        elif any(kw in name_clean for kw in ['quần lửng', 'quần 7 tấc', 'quần 5 tấc', 'capri pants']):
            product_type, sub_category = "bottom", "Quần lửng"
        elif any(kw in name_clean for kw in ['quần dài']):
            product_type, sub_category = "bottom", "Quần dài"
        elif any(kw in name_clean for kw in ['quần']):
            product_type, sub_category = "bottom", "Quần"
        
        # === VÁY/ĐẦM - Từ cụ thể đến tổng quát ===
        
        # Chân váy
        elif any(kw in name_clean for kw in ['chân váy mini', 'váy ngắn']):
            product_type, sub_category = "dress", "Chân váy mini"
        elif any(kw in name_clean for kw in ['chân váy midi', 'váy midi']):
            product_type, sub_category = "dress", "Chân váy midi"
        elif any(kw in name_clean for kw in ['chân váy maxi', 'váy dài', 'váy maxi']):
            product_type, sub_category = "dress", "Chân váy maxi"
        elif any(kw in name_clean for kw in ['chân váy xòe', 'váy xòe', 'váy chữ a', 'a-line skirt']):
            product_type, sub_category = "dress", "Chân váy xòe"
        elif any(kw in name_clean for kw in ['chân váy ôm', 'váy ôm', 'váy bút chì', 'pencil skirt']):
            product_type, sub_category = "dress", "Chân váy ôm"
        elif any(kw in name_clean for kw in ['chân váy xếp ly', 'váy xếp ly', 'pleated skirt']):
            product_type, sub_category = "dress", "Chân váy xếp ly"
        elif any(kw in name_clean for kw in ['chân váy jean', 'váy jean', 'váy bò']):
            product_type, sub_category = "dress", "Chân váy jean"
        elif any(kw in name_clean for kw in ['chân váy']):
            product_type, sub_category = "dress", "Chân váy"
        
        # Đầm/váy liền
        elif any(kw in name_clean for kw in ['đầm suông', 'váy suông', 'shift dress']):
            product_type, sub_category = "dress", "Đầm suông"
        elif any(kw in name_clean for kw in ['đầm ôm', 'váy ôm body', 'bodycon dress']):
            product_type, sub_category = "dress", "Đầm ôm"
        elif any(kw in name_clean for kw in ['đầm xòe', 'váy xòe liền']):
            product_type, sub_category = "dress", "Đầm xòe"
        elif any(kw in name_clean for kw in ['đầm dạ hội', 'váy dạ hội', 'evening dress', 'gown']):
            product_type, sub_category = "dress", "Đầm dạ hội"
        elif any(kw in name_clean for kw in ['đầm công sở', 'váy công sở']):
            product_type, sub_category = "dress", "Đầm công sở"
        elif any(kw in name_clean for kw in ['đầm maxi', 'váy maxi liền', 'maxi dress']):
            product_type, sub_category = "dress", "Đầm maxi"
        elif any(kw in name_clean for kw in ['đầm midi', 'váy midi liền', 'midi dress']):
            product_type, sub_category = "dress", "Đầm midi"
        elif any(kw in name_clean for kw in ['đầm mini', 'váy mini liền', 'mini dress']):
            product_type, sub_category = "dress", "Đầm mini"
        elif any(kw in name_clean for kw in ['đầm', 'váy đầm', 'dress', 'váy liền']):
            product_type, sub_category = "dress", "Đầm"
        elif any(kw in name_clean for kw in ['váy']):
            product_type, sub_category = "dress", "Váy"
        
        # Set/Jumpsuit
        elif any(kw in name_clean for kw in ['jumpsuit', 'yếm quần']):
            product_type, sub_category = "dress", "Jumpsuit"
        elif any(kw in name_clean for kw in ['set đồ', 'bộ đồ', 'set áo quần']):
            product_type, sub_category = "dress", "Set đồ"
        
        # === GIÀY DÉP ===
        
        elif any(kw in name_clean for kw in ['giày sneaker', 'giày thể thao', 'sneakers']):
            product_type, sub_category = "shoe", "Giày sneaker"
        elif any(kw in name_clean for kw in ['giày boot', 'boot', 'bốt', 'giày bốt']):
            product_type, sub_category = "shoe", "Giày boot"
        elif any(kw in name_clean for kw in ['giày cao gót', 'giày gót', 'high heels']):
            product_type, sub_category = "shoe", "Giày cao gót"
        elif any(kw in name_clean for kw in ['giày búp bê', 'búp bê', 'giày bệt']):
            product_type, sub_category = "shoe", "Giày búp bê"
        elif any(kw in name_clean for kw in ['giày lười', 'giày mọi', 'loafer']):
            product_type, sub_category = "shoe", "Giày lười"
        elif any(kw in name_clean for kw in ['giày tây', 'giày da', 'giày công sở']):
            product_type, sub_category = "shoe", "Giày tây"
        elif any(kw in name_clean for kw in ['dép sandal', 'sandal']):
            product_type, sub_category = "shoe", "Dép sandal"
        elif any(kw in name_clean for kw in ['dép lê', 'dép tổ ong', 'dép quai', 'slides']):
            product_type, sub_category = "shoe", "Dép lê"
        elif any(kw in name_clean for kw in ['dép', 'guốc']):
            product_type, sub_category = "shoe", "Dép"
        elif any(kw in name_clean for kw in ['giày']):
            product_type, sub_category = "shoe", "Giày"
        
        # === PHỤ KIỆN ===
        
        elif any(kw in name_clean for kw in ['túi xách', 'túi']):
            product_type, sub_category = "accessory", "Túi xách"
        elif any(kw in name_clean for kw in ['ví tiền', 'ví', 'bóp']):
            product_type, sub_category = "accessory", "Ví"
        elif any(kw in name_clean for kw in ['mũ lưỡi trai', 'nón kết', 'cap']):
            product_type, sub_category = "accessory", "Mũ lưỡi trai"
        elif any(kw in name_clean for kw in ['mũ bucket', 'bucket hat', 'mũ tai bèo']):
            product_type, sub_category = "accessory", "Mũ bucket"
        elif any(kw in name_clean for kw in ['mũ', 'nón']):
            product_type, sub_category = "accessory", "Mũ/Nón"
        elif any(kw in name_clean for kw in ['kính râm', 'kính mát', 'sunglasses']):
            product_type, sub_category = "accessory", "Kính râm"
        elif any(kw in name_clean for kw in ['kính mắt', 'kính']):
            product_type, sub_category = "accessory", "Kính"
        elif any(kw in name_clean for kw in ['dây nịt', 'thắt lưng', 'belt']):
            product_type, sub_category = "accessory", "Dây nịt"
        elif any(kw in name_clean for kw in ['khăn choàng', 'khăn quàng', 'scarf']):
            product_type, sub_category = "accessory", "Khăn choàng"
        elif any(kw in name_clean for kw in ['khăn']):
            product_type, sub_category = "accessory", "Khăn"
        
        # === ĐỐI TƯỢNG ===
        gender = "Unisex"
        if any(kw in name_clean for kw in ['nam', 'men', 'boy', 'bé trai', 'cho nam']):
            gender = "Nam"
        elif any(kw in name_clean for kw in ['nữ', 'women', 'girl', 'bé gái', 'lady', 'cho nữ']):
            gender = "Nữ"
        elif any(kw in name_clean for kw in ['trẻ em', 'bé', 'kid', 'children', 'baby']):
            gender = "Trẻ em"
            
        # === CHẤT LIỆU ===
        material = []
        if any(kw in name_clean for kw in ['cotton', 'bông', 'cô-tông']): material.append("Cotton")
        if any(kw in name_clean for kw in ['kaki', 'khaki']): material.append("Kaki")
        if any(kw in name_clean for kw in ['jean', 'jeans', 'denim', 'bò']): material.append("Jeans")
        if any(kw in name_clean for kw in ['lụa', 'silk', 'lụa tơ tằm']): material.append("Lụa")
        if any(kw in name_clean for kw in ['poly', 'polyester']): material.append("Poly")
        if any(kw in name_clean for kw in ['nỉ', 'fleece']): material.append("Nỉ")
        if any(kw in name_clean for kw in ['len', 'wool', 'dệt kim']): material.append("Len")
        if any(kw in name_clean for kw in ['da', 'leather', 'da thật', 'da pu']): material.append("Da")
        if any(kw in name_clean for kw in ['vải thô', 'linen']): material.append("Vải thô")
        if any(kw in name_clean for kw in ['nhung', 'velvet']): material.append("Nhung")
        if any(kw in name_clean for kw in ['voan', 'chiffon']): material.append("Voan")
        
        # === PHONG CÁCH ===
        style = "Casual"
        if any(kw in name_clean for kw in ['công sở', 'văn phòng', 'formal', 'office']):
            style = "Công sở"
        elif any(kw in name_clean for kw in ['streetwear', 'street', 'hip hop', 'hiphop']):
            style = "Streetwear"
        elif any(kw in name_clean for kw in ['vintage', 'retro', 'cổ điển']):
            style = "Vintage"
        elif any(kw in name_clean for kw in ['hàn quốc', 'ulzzang', 'korean', 'korea', 'style hàn']):
            style = "Hàn Quốc"
        elif any(kw in name_clean for kw in ['nhật bản', 'japanese', 'japan', 'style nhật']):
            style = "Nhật Bản"
        elif any(kw in name_clean for kw in ['thể thao', 'sport', 'gym', 'workout', 'athletic']):
            style = "Thể thao"
        elif any(kw in name_clean for kw in ['dạo phố', 'đi chơi', 'basic', 'casual']):
            style = "Dạo phố"
        elif any(kw in name_clean for kw in ['sang trọng', 'luxury', 'cao cấp', 'elegant']):
            style = "Sang trọng"
        elif any(kw in name_clean for kw in ['sexy', 'gợi cảm']):
            style = "Sexy"
        elif any(kw in name_clean for kw in ['boho', 'bohemian']):
            style = "Boho"
            
        # === CHI TIẾT ===
        details = []
        # Cổ áo
        if any(kw in name_clean for kw in ['cổ tròn', 'cổ tim']): details.append("Cổ tròn")
        if any(kw in name_clean for kw in ['cổ v', 'cổ chữ v']): details.append("Cổ V")
        if any(kw in name_clean for kw in ['cổ cao']): details.append("Cổ cao")
        if any(kw in name_clean for kw in ['cổ bẻ', 'cổ sơ mi']): details.append("Cổ bẻ")
        if any(kw in name_clean for kw in ['cổ vuông']): details.append("Cổ vuông")
        
        # Tay áo
        if any(kw in name_clean for kw in ['tay ngắn', 'ngắn tay']): details.append("Tay ngắn")
        if any(kw in name_clean for kw in ['tay dài', 'dài tay']): details.append("Tay dài")
        if any(kw in name_clean for kw in ['tay lỡ']): details.append("Tay lỡ")
        if any(kw in name_clean for kw in ['không tay', 'tank']): details.append("Không tay")
        if any(kw in name_clean for kw in ['tay bồng', 'tay phồng']): details.append("Tay bồng")
        if any(kw in name_clean for kw in ['tay loe']): details.append("Tay loe")
        
        # Kiểu dáng quần
        if any(kw in name_clean for kw in ['rách', 'ripped']): details.append("Rách")
        if any(kw in name_clean for kw in ['ống rộng', 'wide leg']): details.append("Ống rộng")
        if any(kw in name_clean for kw in ['ống đứng', 'straight']): details.append("Ống đứng")
        if any(kw in name_clean for kw in ['ống côn']): details.append("Ống côn")
        if any(kw in name_clean for kw in ['ống loe', 'flare']): details.append("Ống loe")
        if any(kw in name_clean for kw in ['lưng cao', 'high waist']): details.append("Lưng cao")
        if any(kw in name_clean for kw in ['lưng thấp', 'low waist']): details.append("Lưng thấp")
        if any(kw in name_clean for kw in ['xước', 'wash']): details.append("Xước")
        
        # Form áo
        if any(kw in name_clean for kw in ['form rộng', 'oversize', 'oversiz']): details.append("Oversize")
        if any(kw in name_clean for kw in ['form ôm', 'slim fit', 'ôm body']): details.append("Ôm")
        if any(kw in name_clean for kw in ['form suông']): details.append("Suông")
        
        # Chi tiết khác
        if any(kw in name_clean for kw in ['có túi', 'nhiều túi']): details.append("Có túi")
        if any(kw in name_clean for kw in ['có nón', 'hoodie']): details.append("Có nón")
        if any(kw in name_clean for kw in ['có khóa kéo', 'khóa kéo']): details.append("Có khóa kéo")
        if any(kw in name_clean for kw in ['có nút', 'cài nút']): details.append("Cài nút")
        
        return {
            "category": product_type,
            "sub_category": sub_category,
            "gender": gender,
            "material": ", ".join(material) if material else "Chưa xác định",
            "style": style,
            "details": ", ".join(details) if details else ""
        }

    def extract_shop_id_from_url(self, url):
        match = re.search(r'-i\.(\d+)\.(\d+)', url)
        if match:
            return match.group(1)
        parsed = urlparse(url)
        if parsed.query:
            qs = parse_qs(parsed.query)
            if 'shopid' in qs:
                return qs['shopid'][0]
        return None

    def handle_response(self, response):
        try:
            url = response.url
            if "api" in url:
                print(f"[DEBUG] API Call: {url}") 
                pass

            if "api/v4/search/search_items" in url or "api/v4/shop/rcmd_items" in url or "api/v4/recommend/recommend" in url:
                if response.status == 200:
                    try:
                        data = response.json()
                        items = []
                        if 'items' in data: items = data['items']
                        if 'items' in data and data['items'] is not None: 
                            items = data['items']
                        elif 'data' in data and isinstance(data['data'], dict):
                            if 'items' in data['data'] and data['data']['items'] is not None: 
                                items = data['data']['items']
                            elif 'sections' in data['data']:
                                for section in data['data']['sections']:
                                    if 'data' in section and 'item' in section['data']:
                                         items.extend(section['data']['item'])
                        
                        if items is None: items = []
                        print(f"[API] Found {len(items)} items in API response")
                        
                        for item in items:
                            try:
                                basic = item.get('item_basic', item)
                                itemid = basic.get('itemid')
                                shopid = basic.get('shopid')
                                name = basic.get('name')
                                
                                if not itemid or not name: continue
                                    
                                image = basic.get('image')
                                image_url = f"https://down-vn.img.susercontent.com/file/{image}" if image else ""
                                link = f"https://shopee.vn/product/{shopid}/{itemid}"
                                
                                price_raw = basic.get('price', 0)
                                if price_raw == 0: price_raw = basic.get('price_min', 0)
                                price = float(price_raw) / 100000 if float(price_raw) > 100000 else float(price_raw)

                                cat_info = self.determine_detailed_category(name)
                                
                                product = {
                                    "name": name,
                                    "price": price,
                                    "image": image_url,
                                    "shopee_link": link,
                                    "category": cat_info["category"],
                                    "sub_category": cat_info["sub_category"],
                                    "gender": cat_info["gender"],
                                    "material": cat_info["material"],
                                    "style": cat_info["style"],
                                    "details": cat_info["details"],
                                    "shop_name": f"Shop {shopid}",
                                    "shopid": str(shopid),
                                    "itemid": str(itemid)
                                }
                                
                            # Use itemid as unique key
                                if not any(p['itemid'] == str(itemid) for p in self.products):
                                    self.products.append(product)
                            except Exception as e:
                                print(f"[DEBUG] Error parsing item: {e}")
                    except Exception as e:
                        print(f"[DEBUG] Error processing JSON: {e}")
        except Exception as e:
             print(f"[DEBUG] Error in handle_response: {e}")

    def extract_products_from_html(self, page):
        print("[INFO] Attempting to extract products from HTML...")
        try:
            # Try multiple selectors
            selectors = [
                "div[data-sqe='item']",
                ".shop-search-result-view__item", 
                "div.col-xs-2-4",
                "div.col-xs-2" # Sometimes grid is col-xs-2
            ]
            
            items = []
            for selector in selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"[HTML] Found items using selector: {selector}")
                        items = page.locator(selector).all()
                        break
                except: pass
            
            if len(items) == 0:
                print(f"[HTML] Found 0 item elements with known selectors")
                return

            print(f"[HTML] Found {len(items)} item elements")
            
            for item in items:
                try:
                    # Extract details
                    name = ""
                    # Try name selectors
                    for name_sel in ["div[data-sqe='name']", "._2tW1I8", ".Cve6dx", "div.ie3A+n", "div.efwS5t"]: # various shopee classes
                         if item.locator(name_sel).count() > 0:
                              name = item.locator(name_sel).first.text_content()
                              break
                    
                    if not name:
                         # Fallback text content of the whole item somewhat? No too messy.
                         pass

                    # specific selectors might change, try robust text search or attributes
                    link_elem = item.locator("a").first
                    link = link_elem.get_attribute("href")
                    if link and not link.startswith("http"):
                        link = "https://shopee.vn" + link
                    
                    # Extract ID from link
                    itemid = None
                    shopid = self.shop_id
                    
                    if link:
                        match = re.search(r'i\.(\d+)\.(\d+)', link)
                        if match:
                            shopid = match.group(1)
                            itemid = match.group(2)
                        else:
                             # Try /product/SHOPID/ITEMID
                             match2 = re.search(r'product/(\d+)/(\d+)', link)
                             if match2:
                                 shopid = match2.group(1)
                                 itemid = match2.group(2)

                    if not itemid: 
                        # print(f"[DEBUG] Failed to extract ID from link: {link}")
                        continue

                    img_elem = item.locator("img").first
                    image_url = img_elem.get_attribute("src")
                    
                    # Try to get name from img alt if selectors fail
                    if not name:
                         name = img_elem.get_attribute("alt") or ""
                    
                    # Price selectors - improved extraction
                    price = 0
                    price_selectors = [
                        "span[class*='price']",
                        "div[class*='price']", 
                        "span[class*='text-brand-primary']",
                        ".ZEgDH9",
                        "span._29R_un",
                        "div._3c5u3b",
                        "div[class*='_3e_UQT']",
                        "span[class*='_3e_UQT']"
                    ]
                    
                    for price_sel in price_selectors:
                         if item.locator(price_sel).count() > 0:
                              try:
                                   price_text = item.locator(price_sel).first.text_content()
                                   # Clean price text
                                   price_text = price_text.replace('₫', '').replace('đ', '').replace('.', '').replace(',', '').strip()
                                   # Handle price range (take first price)
                                   if '-' in price_text:
                                        price_text = price_text.split('-')[0].strip()
                                   # Remove any remaining text
                                   price_text = re.sub(r'[^0-9]', '', price_text)
                                   if price_text.isdigit() and int(price_text) > 1000:  # At least 1000 VND
                                        price = float(price_text)
                                        break
                              except: pass
                    
                    # Fallback: parse all text in item and find price-like numbers
                    if price == 0:
                         try:
                              all_text = item.text_content()
                              # Find all numbers in the text
                              numbers = re.findall(r'\d+(?:[.,]\d+)*', all_text)
                              for num_str in numbers:
                                   num_clean = num_str.replace('.', '').replace(',', '')
                                   if num_clean.isdigit():
                                        num = int(num_clean)
                                        # Prices on Shopee are usually between 5,000 and 50,000,000 VND
                                        if 5000 <= num <= 50000000:
                                             price = float(num)
                                             break
                         except: pass

                    if name:
                        cat_info = self.determine_detailed_category(name)
                        product = {
                            "name": name.strip(),
                            "price": price,
                            "image": image_url,
                            "shopee_link": link,
                            "category": cat_info["category"],
                            "sub_category": cat_info["sub_category"],
                            "gender": cat_info["gender"],
                            "material": cat_info["material"],
                            "style": cat_info["style"],
                            "details": cat_info["details"],
                            "shop_name": f"Shop {shopid}",
                            "shopid": str(shopid),
                            "itemid": str(itemid)
                        }
                        
                        if not any(p['itemid'] == str(itemid) for p in self.products):
                            self.products.append(product)
                    else:
                         print(f"[DEBUG] Product name not found for link: {link}")
                except Exception as e:
                    # print(f"[DEBUG] HTML Item Extract Error: {e}")
                    pass
                    
        except Exception as e:
            print(f"[DEBUG] HTML Extract Error: {e}")
            
    def crawl_url(self, url, limit=50):
        print(f"[INFO] Starting crawl for: {url}")
        self.products = []
        self.shop_id = self.extract_shop_id_from_url(url)
        username = None

        # Extract potential username from URL (segment after shopee.vn/)
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) > 0 and '.' in path_parts[0]: # Rough check for username-like segment
             if path_parts[0] not in ['shop', 'product', 'search', 'user', 'api']:
                  username = path_parts[0]

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            page.on("response", self.handle_response)
            
            try:
                target_url = url
                if username:
                     target_url = f"https://shopee.vn/{username}?tab=product"
                     print(f"[REDIRECT] Detected username '{username}', using product tab: {target_url}")
                elif self.shop_id:
                     target_url = f"https://shopee.vn/shop/{self.shop_id}/search?page=0&sortBy=pop"
                     print(f"[REDIRECT] Using Shop ID search URL: {target_url}")
                
                print(f"[NAV] Navigating to {target_url}...")
                page.goto(target_url, timeout=60000, wait_until="networkidle")

                # Attempt HTML extraction immediately after load
                self.extract_products_from_html(page)

                # If we still don't have products 
                if len(self.products) == 0 and not self.shop_id:
                     print("[INFO] Attempting to extract Shop ID from page content...")
                     content = page.content()
                     match = re.search(r'"shopId":\s*(\d+)', content) or \
                            re.search(r'"shopID":\s*(\d+)', content) or \
                            re.search(r'"shopid":\s*(\d+)', content)
                     if match:
                        self.shop_id = match.group(1)
                        print(f"[INFO] Found Shop ID: {self.shop_id}")
                        # Redirect to search which is more likely to have grid
                        target_url = f"https://shopee.vn/shop/{self.shop_id}/search?page=0&sortBy=pop"
                        print(f"[REDIRECT] Fallback to Shop ID URL: {target_url}")
                        page.goto(target_url, timeout=60000, wait_until="networkidle")
                        # Try extraction again after redirect
                        self.extract_products_from_html(page)

                
                # Scroll to load more products
                print("[SCROLL] Scrolling to load products...")
                last_height = page.evaluate("document.body.scrollHeight")
                
                # Scroll loop - do at least a few scrolls
                scrolls = 0
                max_scrolls = 10 
                
                while len(self.products) < limit and scrolls < max_scrolls:
                    # Also try HTML extraction on every scroll if list is empty
                    if len(self.products) == 0:
                        self.extract_products_from_html(page)

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height and len(self.products) > 0:
                        break
                    last_height = new_height
                    scrolls += 1
                
                # Final attempt at HTML extraction
                if len(self.products) == 0:
                    self.extract_products_from_html(page)

                if len(self.products) == 0:
                    print("[WARN] No products found via API or HTML. Saving debug info.")
                    page.screenshot(path="crawler_debug_fail.png")
                         
            except Exception as e:
                print(f"[ERROR] Error during crawl: {e}")
            finally:
                browser.close()
                
        # Deduplicate by itemid
        unique_products = []
        seen_ids = set()
        for p in self.products:
            if p['itemid'] not in seen_ids:
                seen_ids.add(p['itemid'])
                unique_products.append(p)
                
        print(f"[SUCCESS] Crawling finished. Found {len(unique_products)} unique products.")
        return unique_products[:limit]


def crawl_shop_url(url, limit=50):
    crawler = ShopeeCrawler()
    return crawler.crawl_url(url, limit)

if __name__ == "__main__":
    # Test execution
    test_url = "https://shopee.vn/-K%C3%88M-M%C3%9AT-NG%E1%BB%B0C-%C3%A1o-hai-d%C3%A2y-n%E1%BB%AF-tr%C6%A1n-basic-nhi%E1%BB%81u-m%C3%A0u-ch%E1%BA%A5t-thun-g%C3%A2n-m%C3%A1t-m%E1%BA%BB-sexy-c%C3%A1-t%C3%ADnh-%C3%A1o-2-d%C3%A2y-m%E1%BA%B7c-nh%C3%A0-n%E1%BB%AF-t%C3%ADnh-A543-SUTANO-i.184210921.28850598857"
    results = crawl_shop_url(test_url, 10)
    print(json.dumps(results, indent=2, ensure_ascii=False))
