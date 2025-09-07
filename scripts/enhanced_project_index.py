#!/usr/bin/env python3
"""
Enhanced project indexer that automatically includes semantic analysis.
Streamlines the workflow by combining basic indexing with duplicate detection.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Run enhanced indexing with automatic semantic analysis."""
    
    # Get project root (default to current directory)
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    project_path = Path(project_root).resolve()
    
    print("🚀 Enhanced Project Indexing with Semantic Analysis")
    print("=" * 55)
    print(f"📁 Project: {project_path}")
    
    # Step 1: Run basic project indexing
    print("\n📊 Step 1: Building basic project index...")
    try:
        scripts_dir = Path(__file__).parent
        basic_indexer = scripts_dir / "project_index.py" 
        
        result = subprocess.run([
            sys.executable, str(basic_indexer), str(project_path)
        ], capture_output=True, text=True, check=True)
        
        print("✅ Basic index created")
        
        # Show summary from basic indexer
        lines = result.stdout.strip().split('\n')
        for line in lines[-5:]:  # Show last 5 lines (summary)
            if line.strip():
                print(f"   {line}")
                
    except subprocess.CalledProcessError as e:
        print(f"❌ Basic indexing failed: {e}")
        print(f"Error output: {e.stderr}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error in basic indexing: {e}")
        return 1
    
    # Step 2: Run semantic analysis
    print("\n🧠 Step 2: Adding semantic analysis...")
    try:
        semantic_analyzer = scripts_dir / "semantic_analyzer.py"
        index_file = project_path / "PROJECT_INDEX.json"
        
        result = subprocess.run([
            sys.executable, str(semantic_analyzer), 
            str(project_path), str(index_file)
        ], capture_output=True, text=True, check=True)
        
        print("✅ Semantic analysis complete")
        
        # Show semantic analysis summary
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'Analyzing' in line or 'Found' in line or 'complete' in line:
                print(f"   {line}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Semantic analysis failed: {e}")
        print(f"Error output: {e.stderr}")
        print("💡 Make sure scikit-learn is installed: pip install scikit-learn")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error in semantic analysis: {e}")
        return 1
    
    # Step 3: Verify semantic data was saved
    print("\n🔍 Step 3: Verifying semantic integration...")
    try:
        index_file = project_path / "PROJECT_INDEX.json"
        if not index_file.exists():
            raise Exception("PROJECT_INDEX.json not found")
        
        # Check if semantic_index exists in the file
        with open(index_file, 'r') as f:
            content = f.read()
            if '"semantic_index"' in content:
                print("✅ Semantic data successfully integrated")
                
                # Count functions analyzed
                if '"functions"' in content:
                    func_count = content.count('"ast_fingerprint"')
                    print(f"   📊 {func_count} functions analyzed with semantic data")
                
                # Check for similarity clusters
                if '"similarity_clusters"' in content:
                    cluster_start = content.find('"similarity_clusters"')
                    if cluster_start != -1:
                        cluster_section = content[cluster_start:cluster_start+1000]
                        cluster_count = cluster_section.count('"functions"')
                        print(f"   🔗 {cluster_count} similarity clusters detected")
                
                # Check for complexity analysis
                if '"complexity_analysis"' in content:
                    print("   ⚡ Code complexity analysis included")
                
            else:
                raise Exception("Semantic data not found in index")
                
    except Exception as e:
        print(f"❌ Semantic verification failed: {e}")
        return 1
    
    print("\n🎉 Enhanced indexing complete!")
    print("\n📋 Next Steps:")
    print("   • Run duplicate analysis: generate_duplicate_report.py")
    print("   • Set up detection hooks: streamlined_setup.sh")
    print("   • Interactive cleanup: interactive_cleanup.py")
    print("\n💡 Your PROJECT_INDEX.json now includes semantic duplicate detection!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())