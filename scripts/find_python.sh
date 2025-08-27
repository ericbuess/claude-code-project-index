#!/usr/bin/env bash
# Python finder for PROJECT_INDEX
# Finds the newest Python 3.8+ version available

find_python() {
    local min_version_major=3
    local min_version_minor=8
    # Use simple arrays for compatibility with bash 3.2 (macOS default)
    local python_paths=()
    local python_versions_list=()
    local best_cmd=""
    local best_version="0.0"
    
    echo "🔍 Searching for Python versions..." >&2
    
    # First, check if we're in a virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        if command -v python &> /dev/null; then
            local venv_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            if [[ -n "$venv_version" ]]; then
                echo "   📦 Virtual environment detected: Python $venv_version" >&2
                echo "python"
                return 0
            fi
        fi
    fi
    
    # List of Python commands to check
    # We'll check ALL of these to find the newest version
    local python_commands=(
        "python3"
        "python"
        "python3.13"  # Latest stable
        "python3.12"
        "python3.11"
        "python3.10"
        "python3.9"
        "python3.8"  # Minimum supported
    )
    
    # Also check for pythonX.Y in common locations
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS with Homebrew often has versioned Python commands
        for version in {13..8}; do
            python_commands+=("python3.$version")
        done
        # Check Homebrew Python locations
        if [[ -d "/opt/homebrew/bin" ]]; then
            for py in /opt/homebrew/bin/python3.*; do
                if [[ -x "$py" ]]; then
                    python_commands+=("$py")
                fi
            done
        fi
        if [[ -d "/usr/local/bin" ]]; then
            for py in /usr/local/bin/python3.*; do
                if [[ -x "$py" ]]; then
                    python_commands+=("$py")
                fi
            done
        fi
    fi
    
    # Check each Python command and store its version
    for cmd in "${python_commands[@]}"; do
        if command -v "$cmd" &> /dev/null 2>&1 || [[ -x "$cmd" ]]; then
            # Get the actual executable path to avoid checking duplicates
            local full_path=$(command -v "$cmd" 2>/dev/null || echo "$cmd")
            
            # Check if this is actually Python 3 and get version
            local version_output=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null)
            if [[ -n "$version_output" ]]; then
                local major=$(echo "$version_output" | cut -d. -f1)
                local minor=$(echo "$version_output" | cut -d. -f2)
                local micro=$(echo "$version_output" | cut -d. -f3)
                local version="${major}.${minor}"
                
                # Check if version meets minimum requirement
                if [[ "$major" -ge "$min_version_major" ]] && [[ "$minor" -ge "$min_version_minor" || "$major" -gt "$min_version_major" ]]; then
                    # Store this version if we haven't seen this exact Python before
                    local already_found=0
                    for i in "${!python_paths[@]}"; do
                        if [[ "${python_paths[$i]}" == "$full_path" ]]; then
                            already_found=1
                            break
                        fi
                    done
                    
                    if [[ $already_found -eq 0 ]]; then
                        python_paths+=("$full_path")
                        python_versions_list+=("$version")
                        echo "   ✓ Found Python $version.$micro at: $full_path" >&2
                        
                        # Check if this is the best version so far (shell-native comparison)
                        # Compare major.minor as separate integers
                        local best_major=${best_version%%.*}
                        local best_minor=${best_version##*.}
                        local curr_major=${version%%.*}
                        local curr_minor=${version##*.}
                        
                        if [[ $curr_major -gt $best_major ]] || \
                           [[ $curr_major -eq $best_major && $curr_minor -gt $best_minor ]]; then
                            best_version="$version"
                            best_cmd="$cmd"
                        fi
                    fi
                else
                    echo "   ⚠️  Found $cmd (Python $version) but need Python ${min_version_major}.${min_version_minor}+" >&2
                fi
            fi
        fi
    done
    
    if [[ -n "$best_cmd" ]]; then
        echo "" >&2
        echo "   🎯 Selected newest version: Python $best_version" >&2
        echo "      Using: $best_cmd" >&2
        echo "$best_cmd"
        return 0
    else
        echo "" >&2
        echo "❌ Error: Could not find Python ${min_version_major}.${min_version_minor} or higher" >&2
        echo "" >&2
        echo "Please install Python 3.8+ using one of these methods:" >&2
        echo "" >&2
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  • Homebrew: brew install python@3.12" >&2
            echo "  • MacPorts: sudo port install python312" >&2
            echo "  • Download from: https://www.python.org/downloads/" >&2
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "  • Debian/Ubuntu: sudo apt-get install python3" >&2
            echo "  • Fedora: sudo dnf install python3" >&2
            echo "  • Arch: sudo pacman -S python" >&2
            echo "  • Download from: https://www.python.org/downloads/" >&2
        fi
        echo "" >&2
        echo "If Python 3.8+ is already installed but not found, you can:" >&2
        echo "  • Set PYTHON_CMD environment variable: export PYTHON_CMD=/path/to/python3" >&2
        echo "  • Add Python to your PATH" >&2
        echo "" >&2
        echo "To prefer a specific Python version over the newest:" >&2
        echo "  • export PYTHON_CMD=python3.10  (or any specific version)" >&2
        return 1
    fi
}

# Check for environment variable override
if [[ -n "$PYTHON_CMD" ]]; then
    if command -v "$PYTHON_CMD" &> /dev/null; then
        # Verify it meets version requirements (removed 'local' since we're not in a function)
        override_version=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        if [[ -n "$override_version" ]]; then
            echo "   ✓ Using PYTHON_CMD override: $PYTHON_CMD (Python $override_version)" >&2
            echo "$PYTHON_CMD"
            exit 0
        else
            echo "   ⚠️  PYTHON_CMD set to '$PYTHON_CMD' but doesn't appear to be Python" >&2
        fi
    else
        echo "   ⚠️  PYTHON_CMD set to '$PYTHON_CMD' but command not found" >&2
    fi
fi

# If script is run directly (not sourced), find and output Python command
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    find_python
fi