"""Validated context → control → result camera cuts; original source PTS stay unchanged."""
import math

def rect(value,width,height):
    if not isinstance(value,list) or len(value)!=4 or any(type(n) is not int for n in value):raise ValueError('Framing crop uses integer [width,height,x,y]')
    w,h,x,y=value
    if min(w,h)<2 or min(x,y)<0 or x+w>width or y+h>height or w%2 or h%2:raise ValueError('Framing leaves source bounds or has odd dimensions')
    return value

def contained(roi,crop):
    x,y,w,h=roi;cw,ch,cx,cy=crop
    return x>=cx and y>=cy and x+w<=cx+cw and y+h<=cy+ch

def around(roi,context):
    cw,ch,cx,cy=context;x,y,w,h=roi;aspect=cw/ch
    width=min(cw,max(w*1.7,h*aspect*2,200));height=width/aspect
    width=max(2,int(width)//2*2);height=max(2,int(height)//2*2)
    left=max(cx,min(cx+cw-width,int(x+w/2-width/2)//2*2));top=max(cy,min(cy+ch-height,int(y+h/2-height/2)//2*2))
    crop=[width,height,left,top]
    if not contained(roi,crop):raise ValueError('Target/result does not fit its readable crop')
    return crop

def bind(proof,asset,duration):
    width,height=asset['width'],asset['height'];context=rect(proof.get('context_crop',[width//2*2,height//2*2,0,0]),width,height)
    if not contained(proof['target_roi'],context) or not contained(proof['result_roi'],context):raise ValueError('Context crop must include actual target and result')
    frames=round(duration*30);target=round((proof['target']-proof['offset'])*30);result=round((proof['result']-proof['offset'])*30)
    if not 0<=target<result<frames:raise ValueError('Framing events must stay on the retained output frame clock')
    framing=dict(v=1,source_dimensions=[width,height],context=context,focus=around(proof['target_roi'],context),result=around(proof['result_roi'],context),target_frame=target,result_frame=result,frames=frames,
                 controller='THC source-bound hard camera cuts; not an upstream auto-zoom claim')
    validate(framing,width,height);return framing

def validate(f,width,height):
    if set(f)-{'v','source_dimensions','context','focus','result','target_frame','result_frame','frames','controller'} or f.get('v')!=1 or f.get('source_dimensions')!=[width,height]:raise ValueError('Unsupported framing/source identity')
    for key in ('context','focus','result'):rect(f[key],width,height)
    cw,ch,cx,cy=f['context']
    for key in ('focus','result'):
        w,h,x,y=f[key]
        if not contained([x,y,w,h],f['context']) or abs(w/h-cw/ch)>.025:raise ValueError('Framing crop must stay inside context with matching aspect')
    if any(type(f[k]) is not int for k in ('target_frame','result_frame','frames')) or not 0<=f['target_frame']<f['result_frame']<f['frames']<=900:raise ValueError('Invalid source-bound frame clock')
    return f

def map_roi(f,roi,frame):
    crop=f['context'] if frame<f['target_frame'] else f['focus'] if frame<f['result_frame'] else f['result']
    w,h,x,y=crop;rx,ry,rw,rh=roi
    if not contained(roi,crop):raise ValueError('Observed landmark is outside its camera crop')
    # The output viewport uses the context aspect; small even-pixel crop rounding is recorded.
    vh=round(1080*f['context'][1]/f['context'][0]/2)*2;scale_x=1080/w;scale_y=vh/h
    return [(rx-x)*scale_x/1080,((1920-vh)/2+(ry-y)*scale_y)/1920,rw*scale_x/1080,rh*scale_y/1920]

def filter(f,width,height):
    validate(f,width,height);cw,ch,cx,cy=f['context'];fw,fh,fx,fy=f['focus'];rw,rh,rx,ry=f['result'];a=f['target_frame'];b=f['result_frame']
    choice=lambda context,focus,result:f'if(lt(on,{a}),{context},if(lt(on,{b}),{focus},{result}))'
    zoom=choice(1,cw/fw,cw/rw);x=choice(0,fx-cx,rx-cx);y=choice(0,fy-cy,ry-cy);vh=round(1080*ch/cw/2)*2
    if vh>1920:raise ValueError('Use a context crop that fits the protected portrait viewport')
    return f"crop={cw}:{ch}:{cx}:{cy},zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s=1080x{vh}:fps=30,pad=1080:1920:0:(oh-ih)/2"
