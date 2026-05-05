"""
Attention Mechanism for LSTM Models

Implements attention mechanism to help the LSTM focus on relevant
parts of the pitch sequence when making predictions.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class AttentionMechanism(nn.Module):
    """
    Attention mechanism for LSTM sequence processing.
    
    Allows the model to focus on specific parts of the input sequence
    when making predictions, improving performance on pitch sequences.
    """
    
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.hidden_dim = hidden_dim
        
        # Attention parameters
        self.attention_vector = nn.Linear(hidden_dim, hidden_dim)
        self.context_vector = nn.Linear(hidden_dim, 1, bias=False)
        self.tanh = nn.Tanh()
        self.softmax = nn.Softmax(dim=1)
    
    def forward(self, encoder_outputs: torch.Tensor, last_hidden: torch.Tensor) -> torch.Tensor:
        """
        Compute attention weights and context vector.
        
        Args:
            encoder_outputs: LSTM outputs of shape (batch_size, seq_len, hidden_dim)
            last_hidden: Last hidden state of shape (batch_size, hidden_dim)
            
        Returns:
            Context vector of shape (batch_size, hidden_dim)
        """
        batch_size, seq_len, hidden_dim = encoder_outputs.shape
        
        # Compute attention scores
        # Expand last hidden to match sequence length
        hidden_expanded = last_hidden.unsqueeze(1).repeat(1, seq_len, 1)
        
        # Compute energy scores
        energy = self.tanh(self.attention_vector(encoder_outputs) + hidden_expanded)
        
        # Compute attention weights
        attention_scores = self.context_vector(energy).squeeze(2)
        attention_weights = self.softmax(attention_scores)
        
        # Apply attention weights to encoder outputs
        attention_weights = attention_weights.unsqueeze(2)
        context_vector = torch.sum(encoder_outputs * attention_weights, dim=1)
        
        return context_vector
    
    def get_attention_weights(self, encoder_outputs: torch.Tensor, last_hidden: torch.Tensor) -> torch.Tensor:
        """
        Get attention weights for visualization/analysis.
        
        Args:
            encoder_outputs: LSTM outputs of shape (batch_size, seq_len, hidden_dim)
            last_hidden: Last hidden state of shape (batch_size, hidden_dim)
            
        Returns:
            Attention weights of shape (batch_size, seq_len)
        """
        batch_size, seq_len, hidden_dim = encoder_outputs.shape
        
        # Expand last hidden to match sequence length
        hidden_expanded = last_hidden.unsqueeze(1).repeat(1, seq_len, 1)
        
        # Compute energy scores
        energy = self.tanh(self.attention_vector(encoder_outputs) + hidden_expanded)
        
        # Compute attention weights
        attention_scores = self.context_vector(energy).squeeze(2)
        attention_weights = self.softmax(attention_scores)
        
        return attention_weights


class MultiHeadAttention(nn.Module):
    """
    Multi-head attention mechanism for more complex sequence processing.
    
    Allows the model to attend to different aspects of the sequence
    simultaneously through multiple attention heads.
    """
    
    def __init__(self, hidden_dim: int, num_heads: int = 8):
        super().__init__()
        assert hidden_dim % num_heads == 0, "Hidden dimension must be divisible by number of heads"
        
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        
        # Linear projections for queries, keys, and values
        self.query_projection = nn.Linear(hidden_dim, hidden_dim)
        self.key_projection = nn.Linear(hidden_dim, hidden_dim)
        self.value_projection = nn.Linear(hidden_dim, hidden_dim)
        
        # Output projection
        self.output_projection = nn.Linear(hidden_dim, hidden_dim)
        
        # Dropout
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, query: torch.Tensor, key: torch.Tensor, value: torch.Tensor, 
                mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through multi-head attention.
        
        Args:
            query: Query tensor of shape (batch_size, seq_len, hidden_dim)
            key: Key tensor of shape (batch_size, seq_len, hidden_dim)
            value: Value tensor of shape (batch_size, seq_len, hidden_dim)
            mask: Optional attention mask
            
        Returns:
            Output tensor of shape (batch_size, seq_len, hidden_dim)
        """
        batch_size, seq_len, _ = query.shape
        
        # Project to queries, keys, and values
        Q = self.query_projection(query)
        K = self.key_projection(key)
        V = self.value_projection(value)
        
        # Reshape for multi-head attention
        Q = Q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Compute attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.head_dim ** 0.5)
        
        # Apply mask if provided
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        
        # Apply softmax and dropout
        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # Apply attention to values
        context = torch.matmul(attention_weights, V)
        
        # Reshape and project output
        context = context.transpose(1, 2).contiguous().view(
            batch_size, seq_len, self.hidden_dim
        )
        output = self.output_projection(context)
        
        return output


class SelfAttention(nn.Module):
    """
    Self-attention mechanism for sequence processing.
    
    Allows each position in the sequence to attend to all other positions.
    """
    
    def __init__(self, hidden_dim: int, num_heads: int = 8):
        super().__init__()
        self.multi_head = MultiHeadAttention(hidden_dim, num_heads)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through self-attention.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len, hidden_dim)
            mask: Optional attention mask
            
        Returns:
            Output tensor of shape (batch_size, seq_len, hidden_dim)
        """
        # Self-attention
        attention_output = self.multi_head(x, x, x, mask)
        
        # Add and norm
        output = self.layer_norm(x + self.dropout(attention_output))
        
        return output


class CrossAttention(nn.Module):
    """
    Cross-attention mechanism for attending to different sequences.
    
    Useful for attending to different aspects of pitch sequences or game context.
    """
    
    def __init__(self, hidden_dim: int, num_heads: int = 8):
        super().__init__()
        self.multi_head = MultiHeadAttention(hidden_dim, num_heads)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, query: torch.Tensor, key_value: torch.Tensor, 
                mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through cross-attention.
        
        Args:
            query: Query tensor of shape (batch_size, query_len, hidden_dim)
            key_value: Key/Value tensor of shape (batch_size, kv_len, hidden_dim)
            mask: Optional attention mask
            
        Returns:
            Output tensor of shape (batch_size, query_len, hidden_dim)
        """
        # Cross-attention
        attention_output = self.multi_head(query, key_value, key_value, mask)
        
        # Add and norm
        output = self.layer_norm(query + self.dropout(attention_output))
        
        return output
