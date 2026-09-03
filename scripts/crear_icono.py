"""
Crear icono de Hermatron - H azul semigruesa
"""
from PIL import Image, ImageDraw, ImageFont

def crear_icono():
    # Tamaños para el icono
    tamanos = [256, 128, 64, 48, 32, 16]
    imagenes = []
    
    for tamano in tamanos:
        # Crear imagen con fondo transparente
        img = Image.new('RGBA', (tamano, tamano), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Fondo redondeado azul
        padding = tamano // 16
        radio = tamano // 6
        
        # Gradiente azul
        color1 = (0, 123, 255, 255)  # #007BFF
        color2 = (0, 86, 179, 255)   # #0056b3
        
        # Dibujar fondo con esquinas redondeadas
        draw.rounded_rectangle(
            [padding, padding, tamano-padding, tamano-padding],
            radius=radio,
            fill=color1
        )
        
        # Dibujar la letra H
        font_size = int(tamano * 0.6)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Calcular posición centrada
        texto = "H"
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (tamano - text_width) // 2 - bbox[0]
        y = (tamano - text_height) // 2 - bbox[1]
        
        # Dibujar H blanca
        draw.text((x, y), texto, fill=(255, 255, 255, 255), font=font)
        
        imagenes.append(img)
    
    # Guardar como ICO
    icon_path = "C:/WINDOWS/system32/hermatron_agent/static/hermatron.ico"
    imagenes[0].save(
        icon_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in imagenes],
        append_images=imagenes[1:]
    )
    
    print(f"✅ Icono creado: {icon_path}")
    return icon_path

if __name__ == "__main__":
    crear_icono()
