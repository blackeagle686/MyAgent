import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core.tools.bash_tool import BashExecuteTool

def test_bash_direct():
    tool = BashExecuteTool()
    
    # Test 1: Simple command
    print("Testing simple command: ls -d core/")
    result = tool.execute(code="ls -d core/")
    print(f"Result:\n{result}\n")
    
    # Test 2: Multi-line script with pipe
    script = """
    echo "Line 1" > test_file.txt
    echo "Line 2" >> test_file.txt
    cat test_file.txt | grep "Line 2"
    rm test_file.txt
    """
    print(f"Testing script:\n{script}")
    result = tool.execute(code=script)
    print(f"Result:\n{result}\n")

if __name__ == "__main__":
    test_bash_direct()
