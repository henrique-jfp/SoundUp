from pathlib import Path

path = Path(r"C:\Projetos Pessoais\SoundUp\installer\wix\Product.wxs")
text = path.read_text(encoding="utf-8")
text = text.replace('Version="2.0.3.0"', 'Version="2.0.4.0"')
text = text.replace(
    '<RegistryValue Type="string" Name="Version" Value="2.0.3" />',
    '<RegistryValue Type="string" Name="Version" Value="2.0.4" />',
)
path.write_text(text, encoding="utf-8")
print("Product.wxs -> 2.0.4.0")
