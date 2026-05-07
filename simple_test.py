print("Testing basic Python execution")
import sys
print(f"Python version: {sys.version}")
try:
    import baseball
    print("Baseball module imported successfully")
except Exception as e:
    print(f"Baseball import failed: {e}")