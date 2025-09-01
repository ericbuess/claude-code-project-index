#!/usr/bin/env python3
"""
Test runner for PROJECT_INDEX scripts
Runs all tests with comprehensive reporting and coverage
"""

import sys
import unittest
import argparse
from pathlib import Path
from io import StringIO
import time

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent / "tests"))
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

def run_all_tests(verbosity=2, pattern="test_*.py"):
    """Run all tests with specified verbosity and pattern."""
    # Discover and run tests
    test_dir = Path(__file__).parent / "tests"
    loader = unittest.TestLoader()
    suite = loader.discover(str(test_dir), pattern=pattern)
    
    # Custom test result class for better reporting
    class CustomTestResult(unittest.TextTestResult):
        def __init__(self, stream, descriptions, verbosity):
            super().__init__(stream, descriptions, verbosity)
            self.test_times = []
            self.start_time = None
        
        def startTest(self, test):
            super().startTest(test)
            self.start_time = time.time()
        
        def stopTest(self, test):
            super().stopTest(test)
            if self.start_time:
                duration = time.time() - self.start_time
                self.test_times.append((str(test), duration))
    
    # Run tests with custom result class
    stream = sys.stderr if verbosity > 1 else StringIO()
    runner = unittest.TextTestRunner(
        stream=stream, 
        verbosity=verbosity,
        resultclass=CustomTestResult
    )
    
    print("🧪 Running PROJECT_INDEX Test Suite")
    print("=" * 50)
    
    result = runner.run(suite)
    
    # Print summary
    print("\n📊 Test Summary")
    print("-" * 30)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    # Print slowest tests
    if hasattr(result, 'test_times') and result.test_times:
        print("\n⏱️  Slowest Tests:")
        sorted_times = sorted(result.test_times, key=lambda x: x[1], reverse=True)
        for test_name, duration in sorted_times[:5]:
            print(f"  {duration:.3f}s - {test_name}")
    
    # Print failures and errors
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            if verbosity > 1:
                print(f"    {traceback.strip()}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            if verbosity > 1:
                print(f"    {traceback.strip()}")
    
    # Overall result
    success = len(result.failures) == 0 and len(result.errors) == 0
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    return success


def run_specific_test(test_name, verbosity=2):
    """Run a specific test file or test case."""
    if not test_name.endswith('.py'):
        test_name = f"test_{test_name}.py"
    
    # Load the specific test
    test_dir = Path(__file__).parent / "tests"
    loader = unittest.TestLoader()
    
    try:
        if '::' in test_name:
            # Specific test method (e.g., test_find_ollama.py::TestOllamaManager::test_init)
            parts = test_name.split('::')
            module_name = parts[0].replace('.py', '')
            
            if len(parts) == 3:
                # Module::Class::Method
                class_name, method_name = parts[1], parts[2]
                test_path = f"{module_name}.{class_name}.{method_name}"
            elif len(parts) == 2:
                # Module::Class or Module::Method
                test_path = f"{module_name}.{parts[1]}"
            
            suite = loader.loadTestsFromName(test_path)
        else:
            # Entire test file
            module_name = test_name.replace('.py', '')
            suite = loader.discover(str(test_dir), pattern=f"{module_name}.py")
        
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        
        return len(result.failures) == 0 and len(result.errors) == 0
        
    except Exception as e:
        print(f"❌ Error running test '{test_name}': {e}")
        return False


def list_available_tests():
    """List all available test files and test cases."""
    test_dir = Path(__file__).parent / "tests"
    
    print("📋 Available Tests:")
    print("=" * 30)
    
    for test_file in sorted(test_dir.glob("test_*.py")):
        print(f"\n📄 {test_file.name}")
        
        # Try to parse test classes and methods
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Simple regex to find test classes and methods
            import re
            
            classes = re.findall(r'class (Test\w+)\(.*?\):', content)
            for class_name in classes:
                print(f"  📁 {class_name}")
                
                # Find methods in this class
                class_pattern = rf'class {class_name}.*?(?=class|\Z)'
                class_match = re.search(class_pattern, content, re.DOTALL)
                if class_match:
                    class_content = class_match.group(0)
                    methods = re.findall(r'def (test_\w+)', class_content)
                    for method in methods:
                        print(f"    🧪 {method}")
        except Exception:
            print("    (Could not parse test structure)")


def check_test_dependencies():
    """Check if all required dependencies for testing are available."""
    print("🔍 Checking Test Dependencies")
    print("-" * 30)
    
    dependencies = {
        'unittest': 'unittest',
        'unittest.mock': 'unittest.mock',
        'json': 'json',
        'pathlib': 'pathlib'
    }
    
    missing = []
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name}")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        return False
    else:
        print("\n✅ All dependencies available!")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description='Test runner for PROJECT_INDEX scripts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                           # Run all tests
  %(prog)s --list                    # List available tests
  %(prog)s --test find_ollama        # Run find_ollama tests
  %(prog)s --test find_ollama.py::TestOllamaManager  # Run specific test class
  %(prog)s --check-deps              # Check test dependencies
  %(prog)s --quiet                   # Run with minimal output
  %(prog)s --pattern "test_find*"    # Run tests matching pattern
        '''
    )
    
    parser.add_argument('--test', '-t', type=str,
                       help='Run specific test file or test case')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available tests')
    parser.add_argument('--check-deps', action='store_true',
                       help='Check test dependencies')
    parser.add_argument('--pattern', '-p', default="test_*.py",
                       help='Test file pattern (default: test_*.py)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine verbosity
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 3
    else:
        verbosity = 2
    
    # Handle different modes
    if args.check_deps:
        return 0 if check_test_dependencies() else 1
    
    if args.list:
        list_available_tests()
        return 0
    
    if args.test:
        success = run_specific_test(args.test, verbosity)
        return 0 if success else 1
    
    # Run all tests by default
    success = run_all_tests(verbosity, args.pattern)
    return 0 if success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)