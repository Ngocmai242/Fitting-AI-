import torch
import torch.nn as nn
from PIL import Image
import torchvision.transforms as T
import timm
import os

class BodyShapeClassifier(nn.Module):
    """
    EfficientNet-B3 based classifier for Gender and Body Shape.
    Classes: 
    - Female: Apple, Pear, Hourglass, Rectangle, Inverted Triangle
    - Male: Ectomorph, Mesomorph, Endomorph
    """
    def __init__(self, num_classes=8):
        super(BodyShapeClassifier, self).__init__()
        # Load pre-trained EfficientNet-B3
        self.encoder = timm.create_model('efficientnet_b3', pretrained=True)
        
        # Replace the head
        num_features = self.encoder.classifier.in_features
        self.encoder.classifier = nn.Sequential(
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, num_classes)
        )
        
        self.labels = [
            "Female_Apple", "Female_Pear", "Female_Hourglass", 
            "Female_Rectangle", "Female_Inverted_Triangle",
            "Male_Ectomorph", "Male_Mesomorph", "Male_Endomorph"
        ]

    def forward(self, x):
        return self.encoder(x)

class ClassifierEngine:
    def __init__(self, model_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = BodyShapeClassifier().to(self.device)
        
        if model_path and os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        
        self.model.eval()
        
        self.transform = T.Compose([
            T.Resize((300, 300)), # EfficientNet-B3 standard size
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def predict(self, image_bytes):
        from io import BytesIO
        img = Image.open(BytesIO(image_bytes)).convert('RGB')
        img_t = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(img_t)
            probs = torch.softmax(outputs, dim=1)
            conf, pred = torch.max(probs, dim=1)
            
        label = self.model.labels[pred.item()]
        gender, shape = label.split('_', 1)
        
        return {
            "gender": gender,
            "body_shape": shape.replace('_', ' '),
            "confidence": round(conf.item(), 3)
        }

# Strategy for fine-tuning:
# 1. Collect 5000+ images (DeepFashion2 is a good source).
# 2. Use a heuristic script (like our previous MediaPipe logic) to auto-label them as ground truth.
# 3. Use typical CrossEntropyLoss and Adam optimizer.
# 4. Freeze the encoder and only train the head for the first 5 epochs, then unfreeze all.
