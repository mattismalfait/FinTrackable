
import os

file_path = r"C:\Users\malfa\OneDrive\ODILA\Probeersels\FinTrackable\views\dashboard.py"

try:
    with open(file_path, 'rb') as f:
        content = f.read()

    print(f"Read {len(content)} bytes.")
    
    # Try to decode as utf-8
    try:
        text = content.decode('utf-8')
        print("File is valid utf-8.")
    except UnicodeDecodeError:
        print("File is NOT valid utf-8. Attempting to recover.")
        # It's likely mixed. The first part is utf-8.
        # Let's try to decode until error.
        valid_bytes = b""
        extension_bytes = b""
        
        # We know the original file ended around line 430.
        # Let's search for the last known good function 'show_empty_state' or similar.
        # Or just look for null bytes.
        if b'\x00' in content:
            print("Null bytes found.")
            # Remove null bytes (typical artifact of UTF-16 interpreted as ASCII/UTF-8)
            # content = content.replace(b'\x00', b'')
            # This might be dangerous if it merges chars, but for source code usually fine.
            # However, if it was UTF-16, it's: h\x00e\x00l\x00l\x00o\x00
            
            # Let's split by the point where corruption likely started.
            # I appended to the end.
            # Let's try to decode with 'ignore' and see what we get.
            text = content.decode('utf-8', errors='ignore')
            
            # Remove null chars if any remain from ignore? 'ignore' drops bytes that form invalid sequences.
            # Null bytes (0x00) are valid in UTF-8 (as null), but python source code can't have them in strings usually?
            # Actually SyntaxError says "source code string cannot contain null bytes".
            text = text.replace('\x00', '')
            
    # Now write it back cleanly
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print("File rewritten with null bytes removed.")

except Exception as e:
    print(f"Error: {e}")
