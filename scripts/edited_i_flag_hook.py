# File was edited
# Old: def parse_index_flag(prompt):
    """Parse -i, -ic, or -ie flag with optional size.
    Returns: (size_k, clipboard_mode, embedding_mode, cleaned_prompt)
    """
    # Pattern matches -i[number], -ic[number], or -ie[number]
    match = re.search(r'-i([ce]?)(\d+)?(?:\s|$)', prompt)
    
    if not match:
        return None, None, None, prompt
    
    mode_char = match.group(1)
    clipboard_mode = mode_char == 'c'
    embedding_mode = mode_char == 'e'
    
    # If no explicit size provided, check for remembered size
    if match.group(2):
        size_k = int(match.group(2))
    else:
        # For plain -i or -ie without size, try to use last remembered size
        if not clipboard_mode:
            size_k = get_last_interactive_size()
        else:
            # For -ic, always use default
            size_k = DEFAULT_SIZE_K
    
    # Validate size limits
    if size_k < MIN_SIZE_K:
        print(f"⚠️ Minimum size is {MIN_SIZE_K}k, using {MIN_SIZE_K}k", file=sys.stderr)
        size_k = MIN_SIZE_K
    
    if not clipboard_mode and size_k > CLAUDE_MAX_K:
        print(f"⚠️ Claude max is {CLAUDE_MAX_K}k (need buffer for reasoning), using {CLAUDE_MAX_K}k", file=sys.stderr)
        size_k = CLAUDE_MAX_K
    elif clipboard_mode and size_k > EXTERNAL_MAX_K:
        print(f"⚠️ Maximum size is {EXTERNAL_MAX_K}k, using {EXTERNAL_MAX_K}k", file=sys.stderr)
        size_k = EXTERNAL_MAX_K
    
    # Clean prompt (remove flag)
    cleaned_prompt = re.sub(r'-i[ce]?\d*\s*', '', prompt).strip()
    
    return size_k, clipboard_mode, embedding_mode, cleaned_prompt
# New: def parse_index_flag(prompt):
    """Parse -i, -ic, or -ie flag with optional size and similarity options.
    Returns: (size_k, clipboard_mode, embedding_mode, similarity_options, cleaned_prompt)
    """
    # Pattern matches -i[number], -ic[number], or -ie[number]
    match = re.search(r'-i([ce]?)(\d+)?(?:\s|$)', prompt)
    
    if not match:
        return None, None, None, None, prompt
    
    mode_char = match.group(1)
    clipboard_mode = mode_char == 'c'
    embedding_mode = mode_char == 'e'
    
    # Parse similarity-specific options (only valid with -ie)
    similarity_options = {}
    if embedding_mode:
        # Parse --algorithm=algorithm_name
        algo_match = re.search(r'--algorithm[=\s]([a-z-]+)', prompt)
        if algo_match:
            similarity_options['algorithm'] = algo_match.group(1)
            prompt = re.sub(r'--algorithm[=\s][a-z-]+\s*', '', prompt).strip()
        
        # Parse -o output_file or --output=output_file  
        output_match = re.search(r'(?:-o|--output)[=\s](\S+)', prompt)
        if output_match:
            similarity_options['output'] = output_match.group(1)
            prompt = re.sub(r'(?:-o|--output)[=\s]\S+\s*', '', prompt).strip()
        
        # Parse --build-cache
        if '--build-cache' in prompt:
            similarity_options['build_cache'] = True
            prompt = re.sub(r'--build-cache\s*', '', prompt).strip()
        
        # Parse --duplicates
        if '--duplicates' in prompt:
            similarity_options['duplicates'] = True
            prompt = re.sub(r'--duplicates\s*', '', prompt).strip()
        
        # Parse --algorithms=algo1,algo2,algo3 (for cache building)
        algos_match = re.search(r'--algorithms[=\s]([a-z,-]+)', prompt)
        if algos_match:
            similarity_options['algorithms'] = algos_match.group(1).split(',')
            prompt = re.sub(r'--algorithms[=\s][a-z,-]+\s*', '', prompt).strip()
    
    # If no explicit size provided, check for remembered size
    if match.group(2):
        size_k = int(match.group(2))
    else:
        # For plain -i or -ie without size, try to use last remembered size
        if not clipboard_mode:
            size_k = get_last_interactive_size()
        else:
            # For -ic, always use default
            size_k = DEFAULT_SIZE_K
    
    # Validate size limits
    if size_k < MIN_SIZE_K:
        print(f"⚠️ Minimum size is {MIN_SIZE_K}k, using {MIN_SIZE_K}k", file=sys.stderr)
        size_k = MIN_SIZE_K
    
    if not clipboard_mode and size_k > CLAUDE_MAX_K:
        print(f"⚠️ Claude max is {CLAUDE_MAX_K}k (need buffer for reasoning), using {CLAUDE_MAX_K}k", file=sys.stderr)
        size_k = CLAUDE_MAX_K
    elif clipboard_mode and size_k > EXTERNAL_MAX_K:
        print(f"⚠️ Maximum size is {EXTERNAL_MAX_K}k, using {EXTERNAL_MAX_K}k", file=sys.stderr)
        size_k = EXTERNAL_MAX_K
    
    # Clean prompt (remove all flags)
    cleaned_prompt = re.sub(r'-i[ce]?\d*\s*', '', prompt).strip()
    
    return size_k, clipboard_mode, embedding_mode, similarity_options, cleaned_prompt