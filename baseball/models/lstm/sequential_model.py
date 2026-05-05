"""
Sequential LSTM Model for Pitch Prediction

Implements a deep learning model that processes pitch sequences
to predict next pitch outcomes using LSTM architecture with attention.
"""

import asyncio
import numpy as np
import torch
import torch.nn as nn
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from baseball.models.base import BaseModel, ModelPrediction, ModelInfo, PerformanceMetrics
from baseball.models.lstm.pitch_encoder import PitchEncoder
from baseball.models.lstm.attention import AttentionMechanism


@dataclass
class SequenceConfig:
    """Configuration for sequential LSTM model"""
    sequence_length: int = 5
    embedding_dim: int = 64
    hidden_dim: int = 128
    num_layers: int = 2
    dropout: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    device: str = 'cpu'


class SequentialLSTMModel(BaseModel):
    """
    Sequential LSTM model for pitch prediction.
    
    Uses LSTM architecture with attention mechanism to process
    sequences of pitches and predict the next pitch outcome.
    """
    
    def __init__(self, config: Optional[SequenceConfig] = None):
        self.config = config or SequenceConfig()
        self.model = None
        self.encoder = None
        self.attention = None
        self.is_trained = False
        self._performance_metrics = PerformanceMetrics()
        
        # Initialize components
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize model components"""
        self.encoder = PitchEncoder(
            embedding_dim=self.config.embedding_dim,
            sequence_length=self.config.sequence_length
        )
        
        self.attention = AttentionMechanism(
            hidden_dim=self.config.hidden_dim
        )
        
        self.model = PitchSequenceLSTM(
            vocab_size=self.encoder.vocab_size,
            embedding_dim=self.config.embedding_dim,
            hidden_dim=self.config.hidden_dim,
            num_layers=self.config.num_layers,
            dropout=self.config.dropout,
            attention=self.attention
        )
        
        # Move to device
        device = torch.device(self.config.device)
        self.model.to(device)
    
    async def predict(self, context: 'PredictionContext') -> ModelPrediction:
        """
        Predict next pitch given current context.
        
        Args:
            context: Prediction context with pitch sequence and game state
            
        Returns:
            ModelPrediction with pitch probabilities and confidence
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Extract sequence from context
        sequence = self._extract_sequence(context)
        
        # Encode sequence
        encoded_sequence = self.encoder.encode(sequence)
        
        # Make prediction
        with torch.no_grad():
            self.model.eval()
            device = torch.device(self.config.device)
            encoded_tensor = torch.tensor(encoded_sequence).unsqueeze(0).to(device)
            
            logits = self.model(encoded_tensor)
            probabilities = torch.softmax(logits, dim=-1)
            
            # Get top predictions
            top_probs, top_indices = torch.topk(probabilities, k=5)
            
            # Convert to pitch symbols
            predictions = []
            for i, (prob, idx) in enumerate(zip(top_probs[0], top_indices[0])):
                pitch_symbol = self.encoder.decode_idx(idx.item())
                predictions.append({
                    'pitch_symbol': pitch_symbol,
                    'probability': prob.item(),
                    'rank': i + 1
                })
        
        # Calculate confidence
        confidence = self._calculate_confidence(predictions, context)
        
        return ModelPrediction(
            predictions=predictions,
            confidence=confidence,
            model_info=self.get_model_info(),
            timestamp=datetime.now()
        )
    
    def _extract_sequence(self, context: 'PredictionContext') -> List[str]:
        """Extract pitch sequence from prediction context"""
        # Get recent pitches from context
        recent_pitches = context.get('recent_pitches', [])
        
        # Ensure we have the right sequence length
        if len(recent_pitches) < self.config.sequence_length:
            # Pad with unknown symbol
            recent_pitches = ['U'] * (self.config.sequence_length - len(recent_pitches)) + recent_pitches
        elif len(recent_pitches) > self.config.sequence_length:
            # Take most recent
            recent_pitches = recent_pitches[-self.config.sequence_length:]
        
        return recent_pitches
    
    def _calculate_confidence(self, predictions: List[Dict], context: 'PredictionContext') -> float:
        """Calculate prediction confidence based on prediction distribution"""
        if not predictions:
            return 0.0
        
        # Use entropy-based confidence
        probs = [p['probability'] for p in predictions[:3]]  # Top 3 predictions
        entropy = -sum(p * np.log(p + 1e-8) for p in probs)
        
        # Normalize to [0, 1] confidence
        max_entropy = -np.log(1/3)  # Maximum entropy for 3 predictions
        confidence = 1.0 - (entropy / max_entropy)
        
        # Adjust based on sequence completeness
        sequence_completeness = len(context.get('recent_pitches', [])) / self.config.sequence_length
        confidence *= sequence_completeness
        
        return max(0.0, min(1.0, confidence))
    
    async def train(self, training_data: List[Dict]) -> 'TrainingResult':
        """
        Train the LSTM model on pitch sequence data.
        
        Args:
            training_data: List of training examples with sequences and targets
            
        Returns:
            TrainingResult with training metrics
        """
        # Prepare training data
        sequences, targets = self._prepare_training_data(training_data)
        
        # Create data loader
        dataset = PitchSequenceDataset(sequences, targets, self.encoder)
        dataloader = torch.utils.data.DataLoader(
            dataset, 
            batch_size=self.config.batch_size,
            shuffle=True
        )
        
        # Setup training
        device = torch.device(self.config.device)
        optimizer = torch.optim.Adam(
            self.model.parameters(), 
            lr=self.config.learning_rate
        )
        criterion = nn.CrossEntropyLoss()
        
        # Training loop
        self.model.train()
        losses = []
        accuracies = []
        
        for epoch in range(self.config.epochs):
            epoch_loss = 0.0
            epoch_correct = 0
            epoch_total = 0
            
            for batch_sequences, batch_targets in dataloader:
                batch_sequences = batch_sequences.to(device)
                batch_targets = batch_targets.to(device)
                
                # Forward pass
                optimizer.zero_grad()
                logits = self.model(batch_sequences)
                loss = criterion(logits, batch_targets)
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                # Track metrics
                epoch_loss += loss.item()
                predictions = torch.argmax(logits, dim=-1)
                epoch_correct += (predictions == batch_targets).sum().item()
                epoch_total += batch_targets.size(0)
            
            # Calculate epoch metrics
            avg_loss = epoch_loss / len(dataloader)
            accuracy = epoch_correct / epoch_total
            
            losses.append(avg_loss)
            accuracies.append(accuracy)
            
            # Print progress
            if epoch % 10 == 0:
                print(f'Epoch {epoch}: Loss = {avg_loss:.4f}, Accuracy = {accuracy:.4f}')
        
        # Mark as trained
        self.is_trained = True
        
        # Update performance metrics
        self._performance_metrics.accuracy = accuracies[-1]
        self._performance_metrics.training_loss = losses[-1]
        
        return TrainingResult(
            success=True,
            final_accuracy=accuracies[-1],
            final_loss=losses[-1],
            training_epochs=self.config.epochs,
            training_samples=len(training_data)
        )
    
    def _prepare_training_data(self, training_data: List[Dict]) -> Tuple[List[List[str]], List[str]]:
        """Prepare training data from raw format"""
        sequences = []
        targets = []
        
        for example in training_data:
            sequence = example.get('sequence', [])
            target = example.get('target_pitch', '')
            
            if len(sequence) >= self.config.sequence_length and target:
                # Extract sequence of correct length
                seq = sequence[-self.config.sequence_length:]
                sequences.append(seq)
                targets.append(target)
        
        return sequences, targets
    
    def get_model_info(self) -> ModelInfo:
        """Get model information and metadata"""
        return ModelInfo(
            name="SequentialLSTMModel",
            model_type="sequential_deep_learning",
            algorithm="LSTM",
            version="1.0.0",
            description="LSTM model with attention for pitch sequence prediction",
            parameters={
                'sequence_length': self.config.sequence_length,
                'embedding_dim': self.config.embedding_dim,
                'hidden_dim': self.config.hidden_dim,
                'num_layers': self.config.num_layers,
                'vocab_size': self.encoder.vocab_size if self.encoder else 0
            },
            is_trained=self.is_trained,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return self._performance_metrics
    
    def save_model(self, filepath: str):
        """Save model to file"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'encoder': self.encoder,
            'attention': self.attention,
            'config': self.config,
            'is_trained': self.is_trained,
            'performance_metrics': self._performance_metrics
        }, filepath)
    
    def load_model(self, filepath: str):
        """Load model from file"""
        checkpoint = torch.load(filepath, map_location=self.config.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.encoder = checkpoint['encoder']
        self.attention = checkpoint['attention']
        self.config = checkpoint['config']
        self.is_trained = checkpoint['is_trained']
        self._performance_metrics = checkpoint['performance_metrics']


class PitchSequenceLSTM(nn.Module):
    """LSTM model for pitch sequence prediction with attention"""
    
    def __init__(self, vocab_size: int, embedding_dim: int, hidden_dim: int, 
                 num_layers: int, dropout: float, attention: AttentionMechanism):
        super().__init__()
        
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Embedding layer
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        
        # LSTM layers
        self.lstm = nn.LSTM(
            embedding_dim, 
            hidden_dim, 
            num_layers, 
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention mechanism
        self.attention = attention
        
        # Output layer
        self.output_layer = nn.Linear(hidden_dim, vocab_size)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the model.
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length)
            
        Returns:
            Logits tensor of shape (batch_size, vocab_size)
        """
        # Embedding
        embedded = self.embedding(x)  # (batch_size, seq_len, embedding_dim)
        embedded = self.dropout(embedded)
        
        # LSTM
        lstm_out, (hidden, cell) = self.lstm(embedded)  # (batch_size, seq_len, hidden_dim)
        
        # Apply attention to get context vector
        context_vector = self.attention(lstm_out, hidden[-1])  # (batch_size, hidden_dim)
        
        # Output projection
        logits = self.output_layer(context_vector)  # (batch_size, vocab_size)
        
        return logits


class PitchSequenceDataset(torch.utils.data.Dataset):
    """Dataset for pitch sequence training"""
    
    def __init__(self, sequences: List[List[str]], targets: List[str], encoder: PitchEncoder):
        self.sequences = sequences
        self.targets = targets
        self.encoder = encoder
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        sequence = self.sequences[idx]
        target = self.targets[idx]
        
        # Encode sequence
        encoded_sequence = self.encoder.encode(sequence)
        sequence_tensor = torch.tensor(encoded_sequence, dtype=torch.long)
        
        # Encode target
        target_idx = self.encoder.encode_symbol(target)
        target_tensor = torch.tensor(target_idx, dtype=torch.long)
        
        return sequence_tensor, target_tensor


@dataclass
class TrainingResult:
    """Result of model training"""
    success: bool
    final_accuracy: float
    final_loss: float
    training_epochs: int
    training_samples: int
