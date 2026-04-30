import re

def remove_emojis():
    with open('c:/Users/Galax/hermatron_agent/app/video.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Expresión regular para encontrar print(...)
    # y reemplazar caracteres fuera del rango ASCII
    def clean_print(match):
        text = match.group(0)
        return ''.join(c for c in text if ord(c) < 128 or c in 'áéíóúÁÉÍÓÚñÑüÜ')
        
    new_content = re.sub(r'print\([^\)]+\)', clean_print, content)
    
    with open('c:/Users/Galax/hermatron_agent/app/video.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Done")

if __name__ == '__main__':
    remove_emojis()
