"""Plot only audited numerical CSVs. No model or Embedding requests.

Requires reportlab. PNG rendering requires Poppler pdftoppm on PATH or --pdftoppm.
SVG is vector output; PNG is 144 dpi. Temporary PDF render intermediates are removed.
"""
import argparse
import csv
from pathlib import Path
import shutil
import subprocess
import tempfile
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics import renderPDF, renderSVG
from reportlab.lib.colors import HexColor, white

COLORS = ['#64748B','#D08A32','#18857A']
LABELS = ['No Memory','Similarity-only','MemRL (frozen)']

def table(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def chart(title,subtitle,labels,values,maximum,tick,unit,colors,notes,fmt,counts=None):
    w,h=900,480;d=Drawing(w,h)
    d.add(Rect(0,0,w,h,fillColor=white,strokeColor=None))
    d.add(String(34,446,title,fontName='Helvetica-Bold',fontSize=21,fillColor=HexColor('#182A3B')))
    d.add(String(34,422,subtitle,fontName='Helvetica',fontSize=11,fillColor=HexColor('#4C5C6D')))
    d.add(String(34,389,unit,fontName='Helvetica',fontSize=10,fillColor=HexColor('#4C5C6D')))
    bc=VerticalBarChart();bc.x=70;bc.y=112;bc.width=795;bc.height=255
    bc.data=[values];bc.categoryAxis.categoryNames=labels
    bc.valueAxis.valueMin=0;bc.valueAxis.valueMax=maximum;bc.valueAxis.valueStep=tick
    bc.valueAxis.visibleGrid=True;bc.valueAxis.gridStrokeColor=HexColor('#E2E8F0')
    bc.valueAxis.strokeColor=HexColor('#CBD5E1');bc.categoryAxis.strokeColor=HexColor('#CBD5E1')
    bc.valueAxis.labels.fontName='Helvetica';bc.valueAxis.labels.fontSize=10
    bc.categoryAxis.labels.fontName='Helvetica';bc.categoryAxis.labels.fontSize=12
    bc.categoryAxis.labels.dy=-9;bc.barWidth=48;bc.groupSpacing=30
    for j,c in enumerate(colors):bc.bars[(0,j)].fillColor=HexColor(c);bc.bars[(0,j)].strokeColor=None
    d.add(bc)
    for j,v in enumerate(values):
        x=bc.x+(j+.5)*bc.width/len(values);y=bc.y+v/maximum*bc.height
        text=fmt.format(v)
        if counts:text+='  ('+counts[j]+')'
        d.add(String(x,y+10,text,fontName='Helvetica-Bold',fontSize=13,textAnchor='middle',fillColor=HexColor('#182A3B')))
    for j,n in enumerate(notes):d.add(String(34,65-j*16,n,fontName='Helvetica',fontSize=10,fillColor=HexColor('#4C5C6D')))
    return d

def main(data,out,pdftoppm):
    out.mkdir(parents=True,exist_ok=True)
    a=table(data/'alfworld_metrics.csv');h=table(data/'harp_metrics.csv')
    pairs={r['outcome']:int(r['count']) for r in table(data/'harp_pair_counts.csv')}
    common=['Single run; custom subset. Descriptive results, not multi-seed estimates.', 'Source: audited per-task CSVs; see scripts/recompute.py and data/source_hashes.csv.']
    charts={}
    charts['harp_success']=chart('HARP / AIME | Final confirmation','Math answer accuracy | 50 fixed questions per arm; 100 answers',
        [LABELS[0],LABELS[2]],[100*float(r['success_rate']) for r in h],110,20,'Correct answers (%)',[COLORS[0],COLORS[2]],
        ['Net gain: 1 question (+2 percentage points). Output cap: 8,192 tokens per answer.']+common,'{:.0f}%', [r['correct']+'/50' for r in h])
    order=['both_correct','both_wrong','wrong_to_correct','correct_to_wrong']
    charts['harp_paired']=chart('HARP / AIME | Paired outcomes','Direction: No Memory -> MemRL | Same 50 questions',
        ['Both correct','Both wrong','Wrong -> correct','Correct -> wrong'],[pairs[k] for k in order],40,10,'Questions (count)',
        [COLORS[0],'#A6B0BE',COLORS[2],'#BA5661'],['35 + 6 + 5 + 4 = 50. Net gain = 5 - 4 = 1 question.']+common,'{:.0f}')
    charts['alfworld_success']=chart('ALFWorld | Task success','Frozen evaluation | Same 50 valid_unseen challenge tasks',LABELS,
        [100*float(r['success_rate']) for r in a],110,20,'Environment won (%)',COLORS,
        ['Shared trained memory bank. MemRL does not lead similarity-only in success rate.']+common,'{:.0f}%', [r['successes']+'/50' for r in a])
    for name,col,n,note in [('all50','mean_decisions_all50',50,'All tasks, including failures that reached the 50-decision cap.'),
                          ('common47','mean_decisions_common_success',47,'Only the same 47 tasks completed successfully by all three methods.')]:
        charts['alfworld_steps_'+name]=chart('ALFWorld | Mean decision count',f'{n} tasks per method | Lower is better',LABELS,
            [float(r[col]) for r in a],25,5,'Decisions / task',COLORS,[note]+common,'{:.2f}')
    charts['alfworld_tokens']=chart('ALFWorld | Answer-generation tokens','All 50 tasks per method | Input + output; excludes training and Embedding',LABELS,
        [float(r['total_tokens'])/1e6 for r in a],4.5,1,'Solver tokens (millions)',COLORS,
        ['Tokens measure API usage, not billed currency or end-to-end latency.']+common,'{:.3f}M')
    renderer=pdftoppm or shutil.which('pdftoppm')
    for name,d in charts.items():
        renderSVG.drawToFile(d,str(out/(name+'.svg')))
        if renderer:
            with tempfile.TemporaryDirectory(dir=out.resolve(),prefix='render_') as td:
                pdf=Path(td)/'chart.pdf';renderPDF.drawToFile(d,str(pdf))
                subprocess.run([str(renderer),'-png','-singlefile','-r','144',str(pdf),str(out/name)],check=True,capture_output=True)
        print(name+': SVG'+(' + PNG' if renderer else ' (install Poppler for PNG)'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path('data'));p.add_argument('--out',type=Path,default=Path('figures'));p.add_argument('--pdftoppm')
    a=p.parse_args();main(a.data,a.out,a.pdftoppm)
