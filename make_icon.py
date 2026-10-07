from PIL import Image, ImageDraw

# Ícono de PULSO: fondo azul tinta, barras de gráfico y una línea de pulso en cobre
S = 256
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((8, 8, S - 8, S - 8), radius=28, fill="#0E2235")
for i, h in enumerate([64, 104, 144]):
    x = 56 + i * 52
    d.rectangle((x, 204 - h, x + 32, 204), fill="#F3F0E8")
d.line([(36, 122), (88, 122), (112, 72), (142, 168), (166, 104), (220, 104)], fill="#C2502F", width=16,
       joint="curve")
im.save("icono.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
