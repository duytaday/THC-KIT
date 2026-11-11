"""Optional artifact utility: use existing MoneyPrinter venv's Pillow."""
import argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from video_kit import read

p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);a=p.parse_args()
data=read(a.corpus/'intake.json');font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
for page in range(0,len(data['assets']),3):
    sheet=Image.new('RGB',(960,1350),'#101820');draw=ImageDraw.Draw(sheet)
    for row,asset in enumerate(data['assets'][page:page+3]):
        for col,t in enumerate(asset['frame_times_seconds']):
            source=Image.open(a.corpus/asset['id']/f'frame-{col}.png').convert('RGB');image=ImageOps.contain(source,(240,418))
            x=col*240+(240-image.width)//2;y=row*450+30+(418-image.height)//2;sheet.paste(image,(x,y))
            draw.text((col*240+5,row*450+5),f"{asset['id']} {t:.2f}s",font=font,fill='white')
    out=a.corpus/f'sheet-{page//3+1:02}.jpg';sheet.save(out,quality=90);print(out)
