
import os

file_path = r"C:\Users\malfa\OneDrive\ODILA\Probeersels\FinTrackable\views\dashboard.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "":
        continue
    new_lines.append(line)

# This naive approach removes ALL empty lines, which might be too aggressive (removing spacing between functions).
# Better approach: The file view showed explicit double spacing (e.g. line 1 code, line 2 empty, line 3 code).
# It seems every line of code is followed by an empty line.
# Let's check if EVERY non-empty line is followed by an empty line.
# Actually, the file view showed:
# 619:         st.markdown(f"""
# 620: 
# 621:             <div ...

# So yes, it seems interleaved.
# Let's just write non-empty lines, but preserve intentional spacing?
# Intentional spacing would be harder to distinguish.
# Safe bet: Removing all empty lines might squash code, but python doesn't care about vertical whitespace mostly.
# It's better than double spacing.
# But for readability, we might want to keep one empty line if there were two?
# If the pattern is `Code \n \n Code`, then we keep 1.
# If `Code \n Code`, we keep 0 (but resulting in `Code\nCode`).
# The current file likely has `Code \n \n Code` for what used to be 1 empty line, and `Code \n Code` for what used to be 0.
# No, looks like `Code \n` everywhere.

# Let's try to remove blank lines.
cleaned_content = "".join([line for line in lines if line.strip() != ""])

# But wait, indented multiline strings (like the SQL or HTML) rely on newlines.
# If I remove the empty line inside the f-string:
# 619:         st.markdown(f"""
# 620: 
# 621:             <div...
# If I remove 620, it becomes `markdown(f"""<div...` which is fine.

# What about:
# 621:             <div ...
# 622:
# 623:                 <span>...
# Removing 622 makes it `...<div ...>\n    <span>...` which is also fine.

# So removing all blank lines is a safe start to recover density. 
# We can run a formatter later if needed.

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(cleaned_content)

print(f"Removed {len(lines) - len(new_lines)} empty lines.")
