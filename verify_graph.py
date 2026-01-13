
import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from src.graph import NGEGraph
    print("Successfully imported NGEGraph")
    
    graph = NGEGraph()
    print("Successfully initialized NGEGraph")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
