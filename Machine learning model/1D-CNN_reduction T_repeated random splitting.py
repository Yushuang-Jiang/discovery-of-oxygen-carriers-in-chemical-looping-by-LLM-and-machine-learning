import pandas as pd
import numpy as np
import time
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from bayes_opt import BayesianOptimization
from torch.utils.data import DataLoader, TensorDataset

# GPU device
device = torch.device('cuda')

log_file = Path("training_log_T_1D CNN.txt")

def log_message(message):
    """Write logs in real time and print them to the terminal."""
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")


class Model(nn.Module):
    def __init__(self, dropout, conv1_filters, conv2_filters, conv3_filters, dense_size):
        super(Model, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=1, out_channels=conv1_filters, kernel_size=30, padding='same')
        self.relu1 = nn.ReLU()
        self.pool1 = nn.MaxPool1d(kernel_size=3)

        self.conv2 = nn.Conv1d(in_channels=conv1_filters, out_channels=conv2_filters, kernel_size=20, padding='same')
        self.relu2 = nn.ReLU()
        self.pool2 = nn.MaxPool1d(kernel_size=2)

        self.conv3 = nn.Conv1d(in_channels=conv2_filters, out_channels=conv3_filters, kernel_size=10, padding='same')
        self.relu3 = nn.ReLU()
        self.pool3 = nn.MaxPool1d(kernel_size=2)

        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(conv3_filters * 125, dense_size)  # Make sure the input length is correct.
        self.relu4 = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dense_size, 1)

    def forward(self, x):
        x = self.conv1(x)
        x = self.relu1(x)
        x = self.pool1(x)

        x = self.conv2(x)
        x = self.relu2(x)
        x = self.pool2(x)

        x = self.conv3(x)
        x = self.relu3(x)
        x = self.pool3(x)

        x = self.flatten(x)
        x = self.fc1(x)
        x = self.relu4(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


# Read data
file_path = Path("..") / "XRD-T.xlsx"
data = pd.read_excel(file_path)
y = data.iloc[:, 2].values
X = data.iloc[:, 5:1505].values

train_sizes = [0.9, 0.8, 0.7, 0.6, 0.5]
random_states = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,20,21,22,23,42]

for train_size in train_sizes:
    for random_state in random_states:
        start_time = time.time()

        X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=train_size, random_state=random_state)
        X_train = X_train / 100
        X_test = X_test / 100

        # Reshape to (batch_size, channels, sequence_length)
        X_train = X_train.reshape(-1, 1, 1500)
        X_test = X_test.reshape(-1, 1, 1500)

        X_train_tensor = torch.tensor(X_train, dtype=torch.float32).to(device)
        X_test_tensor = torch.tensor(X_test, dtype=torch.float32).to(device)
        y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1).to(device)
        y_test_tensor = torch.tensor(y_test, dtype=torch.float32).view(-1, 1).to(device)

        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        test_dataset = TensorDataset(X_test_tensor, y_test_tensor)

        train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

        def build_and_train_model(dropout, conv1_filters, conv2_filters, conv3_filters, dense_size, learning_rate):
            start_train_time = time.time()

            conv1_filters = int(conv1_filters)
            conv2_filters = int(conv2_filters)
            conv3_filters = int(conv3_filters)
            dense_size = int(dense_size)

            model = Model(dropout, conv1_filters, conv2_filters, conv3_filters, dense_size).to(device)
            criterion = nn.MSELoss()
            optimizer = optim.Adam(model.parameters(), lr=learning_rate)

            for epoch in range(150):
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
            mse_test = mean_squared_error(y_test, test_predictions)
            r2_test = r2_score(y_test, test_predictions)

            elapsed_train_time = time.time() - start_train_time
            log_message(f"Training time (train_size={train_size}, random_state={random_state}): {elapsed_train_time:.2f} seconds")

            if r2_test > 0.5:
                model_name = f"3Con1d-{train_size}_{random_state}_trainMSE_{mse_train:.4f}_trainR2_{r2_train:.4f}_testMSE_{mse_test:.4f}_testR2_{r2_test:.4f}.pt"
                torch.save(model, model_name)

            params_str = f"dropout={dropout:.4f}, conv1_filters={conv1_filters}, " \
                         f"conv2_filters={conv2_filters}, conv3_filters={conv3_filters}, " \
                         f"dense_size={dense_size}, learning_rate={learning_rate:.8f}"

            log_message(f"For train size {train_size}, random_state {random_state}: {params_str} => "
                        f"Train MSE: {mse_train:.6f}, Train R²: {r2_train:.6f}, Test MSE: {mse_test:.6f}, Test R²: {r2_test:.6f}")

            return -mse_test

        pbounds = {
            'dropout': (0, 0.3),
            'conv1_filters': (16, 64),
            'conv2_filters': (16, 64),
            'conv3_filters': (16, 64),
            'dense_size': (128, 1024),
            'learning_rate': (1e-6, 1e-2)
        }

        optimizer = BayesianOptimization(
            f=build_and_train_model,
            pbounds=pbounds,
            random_state=42,
            verbose=2
        )

        optimizer.maximize(init_points=20, n_iter=1000)

        best_params = optimizer.max['params']
        log_message(f"Best parameters for train size={train_size}, random_state={random_state}: {best_params}")
