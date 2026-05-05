"""
Pitch Encoder for LSTM Models

Handles encoding and decoding of pitch symbols for sequential models.
Maps pitch symbols to indices and vice versa for neural network processing.
"""

from typing import Dict, List, Optional
import numpy as np


class PitchEncoder:
    """
    Encoder for pitch symbols used in sequential models.
    
    Maps pitch symbols to integer indices and provides embedding
    functionality for neural network processing.
    """
    
    # Standard Retrosheet pitch symbols
    PITCH_SYMBOLS = [
        'U',  # Unknown/placeholder
        'B',  # Ball
        'C',  # Called strike
        'S',  # Swinging strike
        'F',  # Foul ball
        'K',  # Strikeout (swinging)
        'L',  # Strikeout (looking)
        'M',  # Strikeout (foul tip)
        'O',  # Foul tip (not strikeout)
        'P',  # Pitchout
        'Q',  # Unknown pitch type
        'R',  # Runner advancement on pitch
        'T',  # Foul bunt
        'V',  # Forced strike (bunt attempt)
        'X',  # Ball in play (unknown outcome)
        'D',  # Double (hit)
        'E',  # Error (hit)
        'H',  # Home run
        'I',  # Infield hit (single)
        'J',  # Intentional ball
        'N',  # No pitch (pickoff attempt)
        'W',  # Walk (intentional)
        'Y',  # Single (hit)
        'Z',  # Strikeout (unknown type)
        '.',  # Unknown/placeholder
        '*',  # Wild pitch
        '+',  # Hit by pitch
        '-',  # Run (unearned)
        '/',  # Sacrifice bunt
        '1',  # Single (hit)
        '2',  # Double (hit)
        '3',  # Triple (hit)
    ]
    
    def __init__(self, embedding_dim: int = 64, sequence_length: int = 5):
        self.embedding_dim = embedding_dim
        self.sequence_length = sequence_length
        
        # Create symbol to index mapping
        self.symbol_to_idx = {symbol: idx for idx, symbol in enumerate(self.PITCH_SYMBOLS)}
        self.idx_to_symbol = {idx: symbol for symbol, idx in self.symbol_to_idx.items()}
        self.vocab_size = len(self.PITCH_SYMBOLS)
        
        # Initialize embedding matrix (could be pre-trained later)
        self.embedding_matrix = self._initialize_embeddings()
        
        # Pitch categories for grouping
        self.pitch_categories = self._create_pitch_categories()
    
    def _initialize_embeddings(self) -> np.ndarray:
        """Initialize embedding matrix with random values"""
        # Using Xavier initialization
        scale = np.sqrt(6.0 / (self.vocab_size + self.embedding_dim))
        return np.random.uniform(-scale, scale, (self.vocab_size, self.embedding_dim))
    
    def _create_pitch_categories(self) -> Dict[str, List[str]]:
        """Create pitch categories for grouping similar pitches"""
        return {
            'balls': ['B', 'J', 'W'],  # Balls and intentional balls
            'strikes': ['C', 'S', 'K', 'L', 'M', 'V'],  # All strike types
            'fouls': ['F', 'O', 'T'],  # Foul balls
            'in_play': ['X', 'D', 'E', 'H', 'I', 'Y', '1', '2', '3'],  # Balls in play
            'special': ['P', 'Q', 'R', 'N', '*', '+', '/', '-'],  # Special cases
            'unknown': ['U', '.', 'Z']  # Unknown/placeholder
        }
    
    def encode(self, sequence: List[str]) -> List[int]:
        """
        Encode a sequence of pitch symbols to indices.
        
        Args:
            sequence: List of pitch symbols
            
        Returns:
            List of integer indices
        """
        encoded = []
        for symbol in sequence:
            if symbol in self.symbol_to_idx:
                encoded.append(self.symbol_to_idx[symbol])
            else:
                # Use unknown symbol for unrecognized pitches
                encoded.append(self.symbol_to_idx['U'])
        
        # Pad or truncate to sequence length
        while len(encoded) < self.sequence_length:
            encoded.append(self.symbol_to_idx['U'])
        
        if len(encoded) > self.sequence_length:
            encoded = encoded[-self.sequence_length:]
        
        return encoded
    
    def encode_symbol(self, symbol: str) -> int:
        """
        Encode a single pitch symbol to index.
        
        Args:
            symbol: Pitch symbol
            
        Returns:
            Integer index
        """
        return self.symbol_to_idx.get(symbol, self.symbol_to_idx['U'])
    
    def decode(self, indices: List[int]) -> List[str]:
        """
        Decode a list of indices to pitch symbols.
        
        Args:
            indices: List of integer indices
            
        Returns:
            List of pitch symbols
        """
        decoded = []
        for idx in indices:
            if 0 <= idx < self.vocab_size:
                decoded.append(self.idx_to_symbol[idx])
            else:
                decoded.append('U')
        return decoded
    
    def decode_idx(self, idx: int) -> str:
        """
        Decode a single index to pitch symbol.
        
        Args:
            idx: Integer index
            
        Returns:
            Pitch symbol
        """
        return self.idx_to_symbol.get(idx, 'U')
    
    def get_embedding(self, symbol: str) -> np.ndarray:
        """
        Get embedding vector for a pitch symbol.
        
        Args:
            symbol: Pitch symbol
            
        Returns:
            Embedding vector
        """
        idx = self.encode_symbol(symbol)
        return self.embedding_matrix[idx]
    
    def get_embeddings_batch(self, symbols: List[str]) -> np.ndarray:
        """
        Get embedding vectors for a batch of symbols.
        
        Args:
            symbols: List of pitch symbols
            
        Returns:
            Matrix of embedding vectors
        """
        indices = [self.encode_symbol(symbol) for symbol in symbols]
        return self.embedding_matrix[indices]
    
    def get_category(self, symbol: str) -> Optional[str]:
        """
        Get the category of a pitch symbol.
        
        Args:
            symbol: Pitch symbol
            
        Returns:
            Category name or None if not found
        """
        for category, symbols in self.pitch_categories.items():
            if symbol in symbols:
                return category
        return None
    
    def get_similarity(self, symbol1: str, symbol2: str) -> float:
        """
        Calculate cosine similarity between two pitch symbols.
        
        Args:
            symbol1: First pitch symbol
            symbol2: Second pitch symbol
            
        Returns:
            Cosine similarity score
        """
        emb1 = self.get_embedding(symbol1)
        emb2 = self.get_embedding(symbol2)
        
        # Calculate cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_symbol_stats(self) -> Dict[str, int]:
        """
        Get statistics about the pitch vocabulary.
        
        Returns:
            Dictionary with vocabulary statistics
        """
        category_counts = {}
        for category, symbols in self.pitch_categories.items():
            category_counts[category] = len(symbols)
        
        return {
            'vocab_size': self.vocab_size,
            'embedding_dim': self.embedding_dim,
            'sequence_length': self.sequence_length,
            'category_counts': category_counts,
            'total_symbols': len(self.PITCH_SYMBOLS)
        }
    
    def validate_sequence(self, sequence: List[str]) -> List[str]:
        """
        Validate and clean a pitch sequence.
        
        Args:
            sequence: List of pitch symbols
            
        Returns:
            Validated sequence with invalid symbols replaced
        """
        validated = []
        for symbol in sequence:
            if symbol in self.symbol_to_idx:
                validated.append(symbol)
            else:
                # Replace invalid symbols with unknown
                validated.append('U')
        return validated
    
    def create_one_hot(self, symbol: str) -> np.ndarray:
        """
        Create one-hot encoding for a pitch symbol.
        
        Args:
            symbol: Pitch symbol
            
        Returns:
            One-hot encoded vector
        """
        one_hot = np.zeros(self.vocab_size)
        idx = self.encode_symbol(symbol)
        one_hot[idx] = 1.0
        return one_hot
    
    def create_sequence_one_hot(self, sequence: List[str]) -> np.ndarray:
        """
        Create one-hot encoding for a sequence of pitch symbols.
        
        Args:
            sequence: List of pitch symbols
            
        Returns:
            Matrix of one-hot encoded vectors
        """
        encoded_sequence = self.encode(sequence)
        one_hot_matrix = np.zeros((len(encoded_sequence), self.vocab_size))
        
        for i, idx in enumerate(encoded_sequence):
            one_hot_matrix[i, idx] = 1.0
        
        return one_hot_matrix
