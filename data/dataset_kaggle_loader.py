"""Load Sudoku puzzles from Kaggle dataset (3 Million Sudoku Puzzles with Ratings)."""
import os
from pathlib import Path
from typing import Optional, List
import kagglehub


def get_dataset_path() -> Path:
    """Download and return path to Kaggle Sudoku dataset if not already cached.
    
    Downloads: radcliffe/3-million-sudoku-puzzles-with-ratings
    This dataset contains millions of Sudoku puzzles with difficulty ratings.
    """
    try:
        path = kagglehub.dataset_download("radcliffe/3-million-sudoku-puzzles-with-ratings")
        print(f"✓ Kaggle dataset cached at: {path}")
        return Path(path)
    except Exception as e:
        print(f"✗ Error downloading dataset: {e}")
        print("  Note: Requires Kaggle API credentials in ~/.kaggle/kaggle.json")
        return None


def load_puzzles_from_csv(csv_path: Path, limit: Optional[int] = None) -> List[str]:
    """Load Sudoku puzzle strings from CSV file.
    
    Expected CSV format (from Kaggle dataset):
    - Column 'puzzle': 81-character puzzle string (digits and dots)
    - Column 'difficulty': difficulty rating (1-10 or similar)
    - Column 'solution': solution string
    
    Args:
        csv_path: Path to CSV file
        limit: Maximum number of puzzles to load (None = all)
    
    Returns:
        List of 81-character puzzle strings normalized to use 0 for blanks
    """
    try:
        import pandas as pd
    except ImportError:
        print("✗ pandas not installed. Install with: pip install pandas")
        return []
    
    try:
        df = pd.read_csv(csv_path)
        
        # Check for puzzle column
        if 'puzzle' not in df.columns:
            print(f"✗ 'puzzle' column not found. Available columns: {list(df.columns)}")
            return []
        
        puzzles = []
        for idx, puzzle_str in enumerate(df['puzzle'].head(limit)):
            # Normalize: replace . with 0, keep digits
            normalized = puzzle_str.replace('.', '0').replace('*', '0')
            if len(normalized) == 81:
                puzzles.append(normalized)
            
            if limit and len(puzzles) >= limit:
                break
        
        print(f"✓ Loaded {len(puzzles)} puzzles from {csv_path.name}")
        return puzzles
    
    except Exception as e:
        print(f"✗ Error loading puzzles: {e}")
        return []


def find_csv_files(dataset_path: Path) -> List[Path]:
    """Find all CSV files in the dataset directory."""
    csv_files = list(dataset_path.glob("*.csv"))
    if not csv_files:
        # Try subdirectories
        csv_files = list(dataset_path.glob("**/*.csv"))
    
    return sorted(csv_files)


def load_puzzles_by_difficulty(dataset_path: Path, difficulty: str = "easy") -> List[str]:
    """Load puzzles filtered by difficulty level from Kaggle dataset.
    
    Args:
        dataset_path: Path to extracted Kaggle dataset
        difficulty: Difficulty level ('easy', 'medium', 'hard', 'expert', 'evil')
    
    Returns:
        List of puzzle strings matching difficulty
    """
    csv_files = find_csv_files(dataset_path)
    if not csv_files:
        print(f"✗ No CSV files found in {dataset_path}")
        return []
    
    puzzles = []
    difficulty_map = {
        'easy': (1, 2),
        'medium': (3, 4),
        'hard': (5, 6),
        'expert': (7, 8),
        'evil': (9, 10)
    }
    
    min_diff, max_diff = difficulty_map.get(difficulty.lower(), (1, 10))
    
    try:
        import pandas as pd
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            
            # Check for difficulty column
            if 'difficulty' not in df.columns:
                continue
            
            # Filter by difficulty
            filtered = df[
                (df['difficulty'] >= min_diff) & 
                (df['difficulty'] <= max_diff) &
                (df['puzzle'].str.len() == 81)
            ]
            
            for puzzle_str in filtered['puzzle']:
                normalized = puzzle_str.replace('.', '0').replace('*', '0')
                puzzles.append(normalized)
        
        print(f"✓ Loaded {len(puzzles)} '{difficulty}' puzzles from Kaggle dataset")
        return puzzles
    
    except Exception as e:
        print(f"✗ Error filtering puzzles by difficulty: {e}")
        return []


if __name__ == "__main__":
    # Test: Download dataset and list available files
    dataset_path = get_dataset_path()
    if dataset_path:
        print(f"\nDataset contents:")
        csv_files = find_csv_files(dataset_path)
        for csv_file in csv_files[:5]:
            print(f"  - {csv_file.name}")
        
        if csv_files:
            print(f"\nLoading first 5 puzzles from {csv_files[0].name}:")
            puzzles = load_puzzles_from_csv(csv_files[0], limit=5)
            for i, puzzle in enumerate(puzzles, 1):
                print(f"  {i}. {puzzle[:20]}...")
