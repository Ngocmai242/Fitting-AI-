import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import json
import os
import random
import numpy as np

# --- 1. Mock Dataset Class ---
class OutfitDataset(Dataset):
    def __init__(self, data_path):
        """
        Loads preprocessed data (user_profile, outfit_features, compatibility_score).
        For this demo, we generate synthetic data.
        """
        self.samples = []
        # Simulate 1000 training samples
        for _ in range(1000):
            # User Features: [BodyType(0-3), StylePref(0-4), Height, Weight]
            user_feat = np.random.rand(4).astype(np.float32)
            
            # Outfit Features: [Color(0-1), Style(0-4), Season(0-3)]
            outfit_feat = np.random.rand(3).astype(np.float32)
            
            # Label: Compatibility Score (0.0 to 1.0)
            label = np.random.rand(1).astype(np.float32)
            
            self.samples.append((user_feat, outfit_feat, label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        user, outfit, label = self.samples[idx]
        return torch.tensor(user), torch.tensor(outfit), torch.tensor(label)

# --- 2. Recommendation Model Definition ---
class OutfitRecommenderNet(nn.Module):
    def __init__(self):
        super(OutfitRecommenderNet, self).__init__()
        
        # Combine user (4) + outfit (3) features = 7 input features
        self.fc1 = nn.Linear(7, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1) # Output score
        self.sigmoid = nn.Sigmoid()

    def forward(self, user_feat, outfit_feat):
        x = torch.cat((user_feat, outfit_feat), dim=1)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.relu(x)
        x = self.fc3(x)
        return self.sigmoid(x)

# --- 3. Training Loop ---
def train_model():
    print(">>> Initializing AI Training Pipeline...")
    
    # Hyperparameters
    BATCH_SIZE = 32
    EPOCHS = 10
    LEARNING_RATE = 0.001
    
    # Load Data
    print(">>> Loading/Generating Training Data...")
    dataset = OutfitDataset("data/mock_path.json")
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # Initialize Model
    model = OutfitRecommenderNet()
    criterion = nn.MSELoss() # Using Mean Squared Error for regression (score prediction)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    print(">>> Starting Training Loop...")
    
    for epoch in range(EPOCHS):
        running_loss = 0.0
        for i, data in enumerate(dataloader, 0):
            user_f, outfit_f, labels = data
            
            # Zero the parameter gradients
            optimizer.zero_grad()
            
            # Forward + Backward + Optimize
            outputs = model(user_f, outfit_f)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
        print(f"[Epoch {epoch + 1}] Loss: {running_loss / len(dataloader):.4f}")

    print(">>> Training Complete.")
    
    # Save Model
    save_path = "ai_engine/outfit_recommender.pth"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"✅ Model saved to {save_path}")

if __name__ == "__main__":
    train_model()
