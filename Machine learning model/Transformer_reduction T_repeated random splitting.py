import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from torch.utils.data import DataLoader, TensorDataset
import math
import time
from pathlib import Path
from bayes_opt import BayesianOptimization

device = torch.device('cuda')

log_file = Path("training_log_T.txt")

def log_message(message):
    """Write logs in real time and print them to the terminal."""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=0.1)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class TransformerModel(nn.Module):
    def __init__(self, num_features, d_model, num_heads, num_layers, transformer_dropout, fc_dropout, fc1_size, dim_feedforward, seq_length=30):
        super(TransformerModel, self).__init__()
        self.input_layer = nn.Linear(num_features, d_model)
        self.positional_encoding = PositionalEncoding(d_model, max_len=seq_length)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=d_model, 
                nhead=num_heads, 
                dropout=transformer_dropout, 
                dim_feedforward=dim_feedforward, 
                batch_first=True
            ),
            num_layers=num_layers
        )
        self.fc1 = nn.Linear(d_model * seq_length, fc1_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(fc_dropout)
        self.fc2 = nn.Linear(fc1_size, 1)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.positional_encoding(x)
        x = self.transformer(x)
        x = x.flatten(start_dim=1)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


file_path = Path("..") / "XRD-T.xlsx"
data = pd.read_excel(file_path)
y = data.iloc[:, 2].values
X = data.iloc[:, 5:1505].values

train_sizes = [0.9, 0.8, 0.7, 0.6, 0.5]
random_states = [1,3,5,6,7,8,9,10,11,12,13,14,15,16,17,18,20,21,22,23,24,25,26,42]

for train_size in train_sizes:
    for random_state in random_states:
        start_time = time.time()

        X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=train_size, random_state=random_state)
        X_train = X_train / 100
        X_test = X_test / 100

        X_train = X_train.reshape(-1, 30, 50)
        X_test = X_test.reshape(-1, 30, 50)

        X_train_tensor = torch.tensor(X_train, dtype=torch.float32).to(device)
        X_test_tensor = torch.tensor(X_test, dtype=torch.float32).to(device)
        y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1).to(device)
        y_test_tensor = torch.tensor(y_test, dtype=torch.float32).view(-1, 1).to(device)

        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        test_dataset = TensorDataset(X_test_tensor, y_test_tensor)

        train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

        def optimize_model(learning_rate, dim_feedforward_factor, fc1_size, transformer_dropout, fc_dropout, num_heads_idx):
            start_train_time = time.time()

            learning_rate = float(learning_rate)
            dim_feedforward_factor = int(dim_feedforward_factor)
            dim_feedforward = 64 * dim_feedforward_factor
            fc1_size = int(fc1_size)
            transformer_dropout = float(transformer_dropout)
            fc_dropout = float(fc_dropout)
            num_heads_options = [2, 4, 8]
            num_heads = num_heads_options[int(num_heads_idx)]
            
            model = TransformerModel(
                num_features=50, 
                d_model=64, 
                num_heads=num_heads, 
                num_layers=2, 
                transformer_dropout=transformer_dropout, 
                fc_dropout=fc_dropout, 
                fc1_size=fc1_size,
                dim_feedforward=dim_feedforward 
            ).to(device)
            
            criterion = nn.MSELoss()
            #optimizer = optim.Adam(model.parameters(), lr=learning_rate)
            optimizer = optim.AdamW(model.parameters(), lr=learning_rate, fused=True)
        
            num_epoch = 600
            for epoch in range(num_epoch):
                model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
        
            model.eval()
            with torch.no_grad():
                train_predictions = model(X_train_tensor).cpu().numpy()
                test_predictions = model(X_test_tensor).cpu().numpy()

            mse_train = mean_squared_error(y_train, train_predictions)
            r2_train = r2_score(y_train, train_predictions)
            mae_train = mean_absolute_error(y_train, train_predictions)
            
            mse_test = mean_squared_error(y_test, test_predictions)
            r2_test = r2_score(y_test, test_predictions)
            mae_test = mean_absolute_error(y_test, test_predictions)
        
            elapsed_train_time = time.time() - start_train_time
            log_message(f"Training time (train_size={train_size}, random_state={random_state}): {elapsed_train_time:.2f} seconds")

            if r2_train > 0.85 and r2_test > 0.5:
                model_name = f"Transformer-T-{train_size}_{random_state}_trainMAE_{mae_train:.2f}_trainR2_{r2_train:.4f}_testMAE_{mae_test:.2f}_testR2_{r2_test:.4f}.pt"
                torch.save(model, model_name)
                log_message(f"Saved model: {model_name}")

            params_str = f"transformer_dropout={transformer_dropout:.4f}, fc_dropout={fc_dropout:.4f}, " \
                         f"dim_feedforward={dim_feedforward}, fc1_size={fc1_size}, " \
                         f"num_heads={num_heads}, learning_rate={learning_rate:.8f}"

            log_message(f"For train size {train_size}, random_state {random_state}: {params_str} => "
                        f"Train MAE: {mae_train:.2f}, Train R²: {r2_train:.4f}, Test MAE: {mae_test:.2f}, Test R²: {r2_test:.4f}")

            return -mse_test

        pbounds = {
            'learning_rate': (0.0001, 0.01),
            'dim_feedforward_factor': (2, 6),
            'fc1_size': (128, 1024),
            'transformer_dropout': (0, 0.3),
            'fc_dropout': (0, 0.3),
            'num_heads_idx': (0, 2.99),
        }
        
        optimizer = BayesianOptimization(
            f=optimize_model,
            pbounds=pbounds,
            random_state=42,
            verbose=2
        )
        
        optimizer.maximize(init_points=50, n_iter=1000)
        
        best_params = optimizer.max['params']
        log_message(f"Best parameters for train size={train_size}, random_state={random_state}: {best_params}")

